"""Import jobs: receive a bundle, check it, put its files into Artifactory, record it in the Catalog.

One job per bundle (contract C1). The steps, in order: create (names, signature, space, lock,
first look at what Artifactory and the Catalog already hold), pieces, start, then the run:
verify, rebuild with each piece deleted as it is read, decide the plan, upload with retries,
record, clean up (rules BR1.1-BR1.9).

Plan decision. The signed description does not list the files; the file manifest is inside the
archive. So at create, when the Catalog already holds the version as imported, its recorded files
are compared with Artifactory (complete: skip; absent: repair; differs: fail). When it does not,
the plan stays ``pending`` and is decided after unpacking from the bundle's own manifest
(complete: finish; absent: full; differs: fail).
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import shutil
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg

from modelhub import signing, unpack, verify
from modelhub_artifactory_service import record_builder
from modelhub_artifactory_service.catalog_client import (
    AuthUnavailable,
    CatalogConflict,
    CatalogInvalid,
    CatalogUnavailable,
)
from modelhub_artifactory_service.gateway import (
    ArtifactoryUnreachable,
    UploadError,
    UploadNetworkError,
)
from modelhub_artifactory_service.names import validate_names
from modelhub_artifactory_service.retry import retrying

logger = logging.getLogger("modelhub.import")

MAX_RUNNING = 2
IDLE_LIMIT = timedelta(hours=24)
RUNNING = ("verifying", "uploading", "recording")
OPEN = ("receiving", "ready")
PROGRESS_STEP = 16 << 20
MARGIN = 100 << 20


class ServiceError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.retryable = status, code, message, retryable


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConsumingPieces(unpack.JoinedPieces):
    """Joined pieces that delete each piece once it has been read through (NFR: space)."""

    def readinto(self, buffer) -> int:
        count = super().readinto(buffer)
        done = self._next if count == 0 else max(self._next - 1, 0)
        for path in self._paths[:done]:
            path.unlink(missing_ok=True)
        return count


class _Progress:
    def __init__(self, save) -> None:
        self._save, self._done, self._saved = save, 0, 0

    def advance(self, count: int) -> None:
        self._done += count
        if self._done - self._saved >= PROGRESS_STEP:
            self._saved = self._done
            self._save(self._done)


class Importer:
    def __init__(
        self,
        pool,
        keys,
        gateway,
        catalog,
        work: Path,
        clock=_utc_now,
        sleep=time.sleep,
        jitter=random.random,
    ) -> None:
        self.pool, self.keys, self.gateway, self.catalog = pool, keys, gateway, catalog
        self.work = Path(work)
        self.clock, self.sleep, self.jitter = clock, sleep, jitter
        self.free_bytes = lambda path: shutil.disk_usage(path).free
        self.work.mkdir(parents=True, exist_ok=True)

    # -- reading ------------------------------------------------------------------------------
    def _row(self, import_id: str) -> dict | None:
        with self.pool.connection() as conn:
            return conn.execute(
                "select * from import_jobs where import_id = %s", (import_id,)
            ).fetchone()

    def _owned(self, import_id: str, owner_id: str) -> dict:
        row = self._row(import_id)
        if row is None or row["owner_id"] != owner_id:
            raise ServiceError(404, "not_found", "There is no such import.")
        return row

    @staticmethod
    def _view(row: dict) -> dict:
        error = None
        if row["error_code"]:
            error = {
                "code": row["error_code"],
                "message": row["error_message"],
                "retryable": bool(row["retryable"]),
            }
        return {
            "importId": row["import_id"],
            "modelId": row["model_id"],
            "commit": row["commit"],
            "state": row["state"],
            "plan": row["plan"],
            "outcome": row["outcome"],
            "step": row["step"],
            "bytesDone": row["bytes_done"],
            "bytesTotal": row["bytes_total"],
            "pieceCount": row["piece_count"],
            "createdAt": row["created_at"].isoformat(),
            "endedAt": row["ended_at"].isoformat() if row["ended_at"] else None,
            "error": error,
        }

    def get(self, import_id: str, owner_id: str) -> dict:
        row = self._owned(import_id, owner_id)
        view = self._view(row)
        if row["state"] in OPEN:
            view["missingPieces"] = self._missing(row)
        return view

    def _missing(self, row: dict) -> list[int]:
        with self.pool.connection() as conn:
            have = {
                r["index"]
                for r in conn.execute(
                    "select index from received_pieces where import_id = %s", (row["import_id"],)
                ).fetchall()
            }
        return [n for n in range(1, row["piece_count"] + 1) if n not in have]

    def _set(self, import_id: str, **fields) -> None:
        fields.setdefault("last_activity_at", self.clock())
        names = ", ".join(f"{k} = %s" for k in fields)
        with self.pool.connection() as conn:
            conn.execute(
                f"update import_jobs set {names} where import_id = %s",
                (*fields.values(), import_id),
            )

    def _release(self, import_id: str) -> None:
        with self.pool.connection() as conn:
            conn.execute("delete from model_locks where import_id = %s", (import_id,))
        shutil.rmtree(self.work / import_id, ignore_errors=True)

    def _end(self, import_id: str, state: str, **fields) -> None:
        self._set(import_id, state=state, ended_at=self.clock(), step=None, **fields)
        self._release(import_id)

    # -- create -------------------------------------------------------------------------------
    def create(
        self,
        owner_id: str,
        owner_name: str,
        description_bytes: bytes,
        signature_bytes: bytes,
        computer: str,
        tool_version: str,
        check_results: dict | None,
        bundle_name: str | None = None,
        claimed_model: str | None = None,
        claimed_commit: str | None = None,
    ) -> dict:
        try:
            description = json.loads(description_bytes)
            model_id = description["model"]["id"]
            commit = description["model"]["commit"]
            pieces = description["pieces"]
            stream_size = int(description["stream"]["size"])
            if not pieces or not description.get("complete"):
                raise ValueError("no pieces")
            sig_doc = json.loads(signature_bytes)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ServiceError(
                422, "bundle_invalid", "The bundle description is not readable."
            ) from exc

        if (claimed_model, claimed_commit) not in ((None, None), (model_id, commit)):
            raise ServiceError(
                422, "bundle_invalid", "The model and commit do not match the signed description."
            )
        problem = validate_names(model_id, commit)
        if problem:
            raise ServiceError(422, "invalid_names", problem)
        try:
            key = signing.verify_signature(sig_doc, description_bytes, self.keys.active_docs())
        except signing.SignatureProblem as exc:
            raise ServiceError(422, exc.code, str(exc)) from exc

        with self.pool.connection() as conn:
            same = conn.execute(
                "select import_id from import_jobs where model_key = %s and commit = %s "
                "and owner_id = %s and state = any(%s)",
                (model_id.lower(), commit.lower(), owner_id, list(OPEN)),
            ).fetchone()
        if same:
            self._set(same["import_id"])
            return self.get(same["import_id"], owner_id)

        needed = stream_size + max(stream_size // 50, MARGIN)
        if self.free_bytes(self.work) < needed:
            raise ServiceError(
                507,
                "insufficient_storage",
                f"The import area has too little free space: {needed} bytes are needed.",
            )

        import_id = uuid.uuid4().hex
        now = self.clock()
        row = {
            "import_id": import_id,
            "owner_id": owner_id,
            "owner_name": owner_name,
            "model_id": model_id,
            "commit": commit.lower(),
            "name": bundle_name or description.get("stem") or f"{model_id}@{commit[:12]}",
        }
        self._insert(
            row,
            description_bytes,
            signature_bytes,
            key,
            computer,
            tool_version,
            check_results,
            len(pieces),
            stream_size,
            now,
        )
        try:
            plan = self._plan_at_create(model_id, row["commit"])
        except ServiceError:
            self._delete(import_id)
            raise
        except (CatalogUnavailable, AuthUnavailable, ArtifactoryUnreachable) as exc:
            self._delete(import_id)
            raise self._map(exc) from exc
        if plan == "skip":
            self._record_trail(
                row, key, tool_version, computer, check_results, description_bytes, "skipped"
            )
            self._end(import_id, "skipped", plan="skip", outcome="skipped")
            return self.get(import_id, owner_id)
        self._set(import_id, plan=plan)
        in_dir = self.work / import_id / "in"
        in_dir.mkdir(parents=True)
        (in_dir / "bundle.bundle.json").write_bytes(description_bytes)
        (in_dir / "bundle.bundle.sig").write_bytes(signature_bytes)
        return self.get(import_id, owner_id)

    def _insert(
        self, row, description, signature, key, computer, tool_version, checks, count, size, now
    ) -> None:
        try:
            with self.pool.connection() as conn, conn.transaction():
                conn.execute(
                    "insert into import_jobs (import_id, model_id, model_key, commit, owner_id, "
                    "owner_name, bundle_name, bundle_description, bundle_signature, "
                    "signing_key_fingerprint, computer, tool_version, check_results, plan, state, "
                    "piece_count, bytes_total, created_at, last_activity_at) values (%s, %s, %s, "
                    "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', 'receiving', %s, %s, %s, "
                    "%s)",
                    (
                        row["import_id"],
                        row["model_id"],
                        row["model_id"].lower(),
                        row["commit"],
                        row["owner_id"],
                        row["owner_name"],
                        row["name"],
                        description.decode("utf-8"),
                        signature.decode("utf-8"),
                        key["fingerprint"],
                        computer,
                        tool_version,
                        json.dumps(checks or {}),
                        count,
                        size,
                        now,
                        now,
                    ),
                )
                conn.execute(
                    "insert into model_locks (model_key, import_id, acquired_at) "
                    "values (%s, %s, %s)",
                    (row["model_id"].lower(), row["import_id"], now),
                )
        except psycopg.errors.UniqueViolation as exc:
            raise ServiceError(
                409, "model_locked", "Another import of this model is already running."
            ) from exc

    def _delete(self, import_id: str) -> None:
        with self.pool.connection() as conn:
            conn.execute("delete from import_jobs where import_id = %s", (import_id,))
        shutil.rmtree(self.work / import_id, ignore_errors=True)

    def _plan_at_create(self, model_id: str, commit: str) -> str:
        version = self.catalog.get_version(model_id, commit)
        if not version or version.get("state") != "imported":
            return "pending"
        expected = {
            f["path"]: (f["size_bytes"], f["sha256"])
            for f in version["files"]
            if f.get("downloaded", True)
        }
        listing = self.gateway.list_version(model_id, commit, expected)
        if listing.state == "complete":
            return "skip"
        if listing.state == "absent":
            return "repair"
        raise ServiceError(409, "artifactory_inconsistent", self._differences(listing))

    @staticmethod
    def _differences(listing) -> str:
        shown = "; ".join(listing.differences[:5])
        return f"Artifactory holds a different set of files for this version: {shown}"

    def _job_info(self, row: dict, key_fp: str, computer, tool_version, checks, outcome) -> dict:
        return {
            "imported_by_id": row["owner_id"],
            "imported_by_name": row["owner_name"],
            "imported_at": self.clock().isoformat().replace("+00:00", "Z"),
            "computer": computer,
            "bundle_name": row.get("name") or row["bundle_name"],
            "tool_version": tool_version,
            "check_results": checks or {},
            "outcome": outcome,
            "signing_key_fingerprint": key_fp,
        }

    def _record_trail(self, row, key, tool_version, computer, checks, description, outcome) -> None:
        info = self._job_info(row, key["fingerprint"], computer, tool_version, checks, outcome)
        record = {"importRecord": record_builder.import_record(info, description)}
        retrying(
            lambda: self.catalog.put_import_only(row["model_id"], row["commit"], record),
            retry_on=(CatalogUnavailable,),
            sleep=lambda s: self.sleep(s),
            jitter=self.jitter,
        )

    # -- pieces -------------------------------------------------------------------------------
    def put_piece(self, import_id: str, owner_id: str, index: int, stream, sha256: str) -> None:
        job = self._owned(import_id, owner_id)
        if job["state"] not in OPEN:
            raise ServiceError(409, "wrong_state", "This import is no longer receiving pieces.")
        description = json.loads(job["bundle_description"])
        pieces = description["pieces"]
        if not 1 <= index <= len(pieces):
            raise ServiceError(404, "unknown_piece", f"There is no piece number {index}.")
        declared = pieces[index - 1]
        if sha256 != declared["sha256"]:
            raise ServiceError(422, "piece_damaged", f"Piece {index} is not the one described.")
        target = self.work / import_id / "in" / declared["name"]
        temp = target.with_name("." + target.name + ".tmp")
        digest, total = hashlib.sha256(), 0
        try:
            with open(temp, "wb") as out:
                while chunk := stream.read(1 << 20):
                    total += len(chunk)
                    if total > declared["size"]:
                        raise ServiceError(
                            413, "piece_too_large", f"Piece {index} is larger than described."
                        )
                    digest.update(chunk)
                    out.write(chunk)
            if total != declared["size"] or digest.hexdigest() != declared["sha256"]:
                raise ServiceError(
                    422, "piece_damaged", f"Piece {index} arrived damaged; send it again."
                )
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)
        with self.pool.connection() as conn:
            conn.execute(
                "insert into received_pieces (import_id, index, sha256, size_bytes) "
                "values (%s, %s, %s, %s) on conflict (import_id, index) do nothing",
                (import_id, index, declared["sha256"], total),
            )
        self._set(import_id)

    # -- start --------------------------------------------------------------------------------
    def start(self, import_id: str, owner_id: str) -> dict:
        job = self._owned(import_id, owner_id)
        if job["state"] not in OPEN:
            raise ServiceError(409, "wrong_state", "This import cannot be started now.")
        missing = self._missing(job)
        if missing:
            shown = ", ".join(str(n) for n in missing[:20])
            raise ServiceError(409, "pieces_missing", f"Pieces still to send: {shown}.")
        with self.pool.connection() as conn, conn.transaction():
            conn.execute("select pg_advisory_xact_lock(7340003)")
            running = conn.execute(
                "select count(*) as n from import_jobs where state = any(%s)", (list(RUNNING),)
            ).fetchone()["n"]
            if running >= MAX_RUNNING:
                raise ServiceError(
                    503,
                    "service_busy",
                    "The service is running its limit of imports; try later.",
                    retryable=True,
                )
            conn.execute(
                "update import_jobs set state = 'verifying', step = 'verifying', "
                "last_activity_at = %s where import_id = %s",
                (self.clock(), import_id),
            )
        return self.get(import_id, owner_id)

    # -- run ----------------------------------------------------------------------------------
    def run(self, import_id: str) -> None:
        job = self._row(import_id)
        if job is None or job["state"] != "verifying":
            return
        try:
            outcome, plan = self._execute(job)
        except Exception as exc:
            error = exc if isinstance(exc, ServiceError) else self._map(exc)
            if error.code == "internal_error":
                logger.exception("import %s failed", import_id)
            self._end(
                import_id,
                "failed",
                outcome="failed",
                error_code=error.code,
                error_message=error.message,
                retryable=error.retryable,
            )
            return
        self._end(import_id, "done", plan=plan, outcome=outcome)

    @staticmethod
    def _map(exc: Exception) -> ServiceError:
        if isinstance(exc, (unpack.IntegrityFailure, unpack.UnsafeArchive)):
            return ServiceError(422, "bundle_damaged", str(exc))
        if isinstance(exc, UploadError):
            return ServiceError(502, exc.code, exc.message, getattr(exc, "retryable", False))
        if isinstance(exc, ArtifactoryUnreachable):
            return ServiceError(503, "artifactory_unreachable", str(exc), True)
        if isinstance(exc, CatalogUnavailable):
            return ServiceError(503, "catalog_unavailable", str(exc), True)
        if isinstance(exc, AuthUnavailable):
            return ServiceError(503, "auth_unavailable", str(exc), True)
        if isinstance(exc, CatalogConflict):
            return ServiceError(409, "record_conflict", "The Catalog holds a different record.")
        if isinstance(exc, CatalogInvalid):
            return ServiceError(422, "record_invalid", str(exc))
        return ServiceError(500, "internal_error", "The import failed unexpectedly.")

    def _retry(self, fn, retry_on):
        return retrying(fn, retry_on=retry_on, sleep=lambda s: self.sleep(s), jitter=self.jitter)

    def _execute(self, job: dict) -> tuple[str, str]:
        import_id, model_id, commit = job["import_id"], job["model_id"], job["commit"]
        in_dir, out = self.work / import_id / "in", self.work / import_id / "out"

        reports = verify.verify_bundle([in_dir], trusted=self.keys.active_docs())
        report = reports[0] if reports else None
        if report is None or report.problems:
            first = report.problems[0] if report else None
            raise ServiceError(
                422,
                first.code if first else "bundle_invalid",
                first.message if first else "No bundle was found.",
            )

        self._set(import_id, step="unpacking", bytes_done=0)
        progress = _Progress(lambda done: self._set(import_id, bytes_done=done))
        unpack.rebuild_into(report, out, progress=progress, joined_factory=ConsumingPieces)
        self._set(import_id, bytes_done=job["bytes_total"])

        c1 = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        expected = {f["path"]: (f["size"], f["sha256"]) for f in c1["files"]}
        plan = job["plan"]
        if plan == "pending":
            listing = self._retry(
                lambda: self.gateway.list_version(model_id, commit, expected),
                (ArtifactoryUnreachable,),
            )
            if listing.state == "inconsistent":
                raise ServiceError(409, "artifactory_inconsistent", self._differences(listing))
            plan = "finish" if listing.state == "complete" else "full"
            self._set(import_id, plan=plan)

        if plan in ("full", "repair"):
            self._set(import_id, state="uploading", step="uploading")
            self._retry(
                lambda: self.gateway.uploader.upload(out / "files", model_id, commit),
                (ArtifactoryUnreachable, UploadNetworkError),
            )
            listing = self._retry(
                lambda: self.gateway.list_version(model_id, commit, expected),
                (ArtifactoryUnreachable,),
            )
            if listing.state != "complete":
                raise ServiceError(
                    502,
                    "upload_incomplete",
                    "Artifactory does not hold every file after upload.",
                    retryable=True,
                )

        self._set(import_id, state="recording", step="recording")
        outcome = "imported" if plan == "full" else "completed"
        info = self._job_info(
            job,
            job["signing_key_fingerprint"],
            job["computer"],
            job["tool_version"],
            job["check_results"],
            "imported" if plan == "full" else "repaired",
        )
        info["imported_at"] = job["created_at"].isoformat().replace("+00:00", "Z")
        description = in_dir / "bundle.bundle.json"
        record, documents = record_builder.build_record(
            out, info, description, in_dir / "bundle.bundle.sig"
        )
        if plan == "repair":
            self._retry(
                lambda: self.catalog.put_import_only(
                    model_id, commit, {"importRecord": record["importRecord"]}
                ),
                (CatalogUnavailable,),
            )
        else:
            self._retry(
                lambda: self.catalog.put_version(model_id, commit, record, documents),
                (CatalogUnavailable,),
            )
        return outcome, plan

    # -- cancel and sweeps --------------------------------------------------------------------
    def cancel(self, import_id: str, owner_id: str) -> dict:
        job = self._owned(import_id, owner_id)
        if job["state"] not in OPEN:
            raise ServiceError(409, "wrong_state", "This import can no longer be cancelled.")
        self._end(import_id, "cancelled")
        return self.get(import_id, owner_id)

    def sweep_idle(self) -> int:
        cutoff = self.clock() - IDLE_LIMIT
        with self.pool.connection() as conn:
            rows = conn.execute(
                "select import_id from import_jobs where state = any(%s) and last_activity_at < %s",
                (list(OPEN), cutoff),
            ).fetchall()
        for row in rows:
            self._end(
                row["import_id"],
                "cancelled",
                error_code="idle_timeout",
                error_message="Cancelled after a day with no activity.",
                retryable=True,
            )
        return len(rows)

    def sweep_restart(self) -> int:
        with self.pool.connection() as conn:
            rows = conn.execute(
                "select import_id from import_jobs where state = any(%s)", (list(RUNNING),)
            ).fetchall()
        for row in rows:
            self._end(
                row["import_id"],
                "failed",
                outcome="failed",
                error_code="interrupted",
                error_message="The service restarted while this import was running; run it again.",
                retryable=True,
            )
        with self.pool.connection() as conn:
            live = {
                r["import_id"] for r in conn.execute("select import_id from import_jobs").fetchall()
            }
        for path in self.work.iterdir():
            if path.is_dir() and path.name not in live:
                shutil.rmtree(path, ignore_errors=True)
        return len(rows)
