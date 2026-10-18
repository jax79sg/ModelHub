"""Send verified bundles to the import service and report what happened (contract C1).

One bundle at a time, in the order given: verify here, create the import, send the pieces the
service is missing, start it, and watch it until the service ends it. Every request is safe to
repeat, so network trouble is retried (BR1.5 to BR1.8, BR1.14).
"""

from __future__ import annotations

import json
import random
import socket
import ssl
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from modelhub import __version__, redact, verify
from modelhub.pieces import stem_for
from modelhub.progress import NullReporter
from modelhub.record import utc_now

RETRY_WAITS = (1, 2, 4, 8, 16)
BLOCK = 1 << 20
POLL_SECONDS = 1  # so a finished import is reported within 2 seconds even on a slow link (NFR1.1)
BUSY_POLL_SECONDS = 60
BUSY_WAIT_MINUTES = 30
DONE_STATES = {"done", "failed", "skipped", "cancelled"}


class RunStopped(Exception):
    """The whole run cannot go on (not signed in, program too old). Exit status 2."""


class ServiceError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.retryable = status, code, message, retryable


class Interrupted(Exception):
    """Ctrl-C: stop at once and leave the import on the service to be resumed (BR1.8)."""

    def __init__(self, report: RunReport, unfinished: list[str]) -> None:
        super().__init__("interrupted")
        self.report, self.unfinished = report, unfinished


class PackageFailed(Exception):
    def __init__(self, reason: str, code: str | None = None) -> None:
        super().__init__(reason)
        self.reason, self.code = reason, code


@dataclass
class PieceFile:
    index: int
    path: Path
    size: int
    sha256: str


@dataclass
class Package:
    model_id: str
    commit: str
    bundle_name: str
    description_text: str
    signature_text: str
    pieces: list[PieceFile]
    check_results: dict


@dataclass
class Entry:
    model_id: str
    commit: str
    result: str  # imported | skipped | completed | failed
    reason: str | None = None
    code: str | None = None

    def line(self) -> str:
        head = f"{self.result.upper():9} {self.model_id} {self.commit[:12]}"
        return f"{head}  {self.reason}" if self.reason else head


@dataclass
class RunReport:
    entries: list[Entry] = field(default_factory=list)

    def count(self, result: str) -> int:
        return sum(1 for e in self.entries if e.result == result)

    @property
    def exit_status(self) -> int:
        return 1 if self.count("failed") else 0

    def summary(self) -> str:
        return (
            f"{self.count('imported')} imported, {self.count('completed')} completed, "
            f"{self.count('skipped')} skipped, {self.count('failed')} failed"
        )


# --- finding and checking bundles ---------------------------------------------------------------
def find_descriptions(arguments: list[Path]) -> list[Path]:
    """The ``.bundle.json`` files named by the arguments: a description, a piece, or a folder."""
    found: list[Path] = []
    for argument in arguments:
        path = Path(argument)
        if path.is_dir():
            found += sorted(path.glob("*.bundle.json"))
        elif path.name.endswith(".bundle.json"):
            found.append(path)
        elif ".part-" in path.name:
            stem = path.name.split(".part-")[0]
            found.append(path.with_name(stem + ".bundle.json"))
        else:
            found.append(path)
    seen: set[Path] = set()
    unique = []
    for path in found:
        key = path.resolve()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def prepare(description: Path, progress=None) -> Package:
    """Check one bundle here (signature by a trusted key, every piece) and make it ready to send."""
    if not description.is_file():
        raise PackageFailed(f"{description} was not found")
    stem = description.name[: -len(".bundle.json")]
    reports = verify.verify_bundle([description.parent], progress=progress, only={stem})
    report = next((r for r in reports if r.stem == stem), None)
    if report is None:
        raise PackageFailed(f"{description.name}: no bundle found")
    if report.problems:
        raise PackageFailed("; ".join(p.message for p in report.problems))
    manifest = report.manifest
    model = manifest["model"]
    paths = {p.name: p for p in report.piece_paths}
    pieces = [
        PieceFile(number, paths[piece["name"]], piece["size"], piece["sha256"])
        for number, piece in enumerate(manifest["pieces"], start=1)
    ]
    signature = description.with_name(stem + ".bundle.sig")
    return Package(
        model_id=model["id"],
        commit=model["commit"],
        bundle_name=stem or stem_for(model["id"], model["commit"]),
        description_text=description.read_text(encoding="utf-8"),
        signature_text=signature.read_text(encoding="utf-8"),
        pieces=pieces,
        check_results={
            "pieces": len(pieces),
            "bytes": sum(p.size for p in pieces),
            "signedBy": report_fingerprint(signature),
            "checkedAt": utc_now(),
        },
    )


def report_fingerprint(signature: Path) -> str | None:
    try:
        return json.loads(signature.read_text(encoding="utf-8")).get("fingerprint")
    except (OSError, ValueError):
        return None


# --- talking to the service ---------------------------------------------------------------------
def _caused_by_certificate(error: BaseException) -> bool:
    while error is not None:
        if isinstance(error, ssl.SSLError):
            return True
        error = error.__cause__ or error.__context__
    return False


class ServiceClient:
    def __init__(
        self,
        server: str,
        token: str,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] | None = None,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self._base = server.rstrip("/")
        self._token = token
        self._http = http or httpx.Client(timeout=httpx.Timeout(60, connect=10))
        self._sleep, self._jitter = sleep or (lambda s: time.sleep(s)), jitter
        redact.remember(token)

    def _headers(self, extra: dict | None = None) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "X-Modelhub-Client": __version__,
            **(extra or {}),
        }

    def request(
        self,
        method: str,
        path: str,
        body: Callable[[], Iterator[bytes]] | None = None,
        headers: dict | None = None,
        never_retry: tuple[str, ...] = (),
        **kw,
    ) -> httpx.Response:
        """Send; repeat on network trouble and retryable answers (1, 2, 4, 8, 16 s); raise the rest."""
        last: ServiceError | None = None
        for attempt in range(len(RETRY_WAITS) + 1):
            if attempt:
                self._sleep(RETRY_WAITS[attempt - 1] + self._jitter())
            try:
                content = body() if body else None
                response = self._http.request(
                    method, self._base + path, headers=self._headers(headers), content=content, **kw
                )
            except httpx.HTTPError as error:
                if _caused_by_certificate(error):
                    raise ServiceError(
                        0, "certificate_untrusted", "The server's certificate is not trusted."
                    ) from error
                last = ServiceError(0, "network", "The server could not be reached.", True)
                continue
            if response.status_code < 400:
                return response
            error = self._error(response)
            if response.status_code == 401:
                raise RunStopped(error.message)
            if response.status_code == 426:
                raise RunStopped(error.message)
            if error.code in never_retry or not error.retryable:
                raise error
            last = error
        raise last  # type: ignore[misc]

    @staticmethod
    def _error(response: httpx.Response) -> ServiceError:
        try:
            data = response.json()
        except ValueError:
            data = {}
        message = redact.redact(
            str(data.get("message") or f"The service answered {response.status_code}.")
        )
        retryable = bool(data.get("retryable")) or response.status_code >= 500
        return ServiceError(
            response.status_code, str(data.get("code") or "error"), message, retryable
        )


def _blocks(path: Path, on_block: Callable[[int], None]) -> Callable[[], Iterator[bytes]]:
    def make() -> Iterator[bytes]:
        with open(path, "rb") as handle:
            while chunk := handle.read(BLOCK):
                on_block(len(chunk))
                yield chunk

    return make


def send_package(
    client: ServiceClient,
    package: Package,
    reporter=None,
    sleep: Callable[[float], None] | None = None,
    clock: Callable[[], float] | None = None,
    computer: str | None = None,
) -> Entry:
    sleep, clock = sleep or time.sleep, clock or time.monotonic
    reporter = reporter or NullReporter()
    model, commit = package.model_id, package.commit

    def failed(error: ServiceError) -> Entry:
        return Entry(model, commit, "failed", error.message, error.code)

    try:
        created = client.request(
            "POST",
            "/v1/imports",
            json={
                "modelId": model,
                "commit": commit,
                "bundleName": package.bundle_name,
                "bundleDescription": package.description_text,
                "bundleSignature": package.signature_text,
                "computer": computer or socket.gethostname(),
                "toolVersion": __version__,
                "checkResults": package.check_results,
            },
        )
        job = created.json()
        if created.status_code == 200 or job.get("state") == "skipped":
            return Entry(model, commit, "skipped", "already imported")
        import_id = job["importId"]
        missing = (
            job["missingPieces"] if "missingPieces" in job else [p.index for p in package.pieces]
        )
        by_index = {p.index: p for p in package.pieces}
        todo = [by_index[n] for n in sorted(missing) if n in by_index]
        reporter.start(f"Sending {model}", total_bytes=sum(p.size for p in todo))
        for piece in todo:
            _send_piece(client, import_id, piece, reporter)
        reporter.finish()
        _start(client, import_id, reporter, sleep, clock)
        return _watch(client, import_id, package, reporter, sleep)
    except ServiceError as error:
        reporter.finish()
        return failed(error)


def _send_piece(client: ServiceClient, import_id: str, piece: PieceFile, reporter) -> None:
    for attempt in (1, 2):
        sent = [0]

        def count(n: int, sent=sent) -> None:
            sent[0] += n
            reporter.advance(n)

        try:
            client.request(
                "PUT",
                f"/v1/imports/{import_id}/pieces/{piece.index}",
                body=_blocks(piece.path, count),
                headers={
                    "X-Piece-SHA256": piece.sha256,
                    "Content-Type": "application/octet-stream",
                    "Content-Length": str(piece.size),
                },
                never_retry=("piece_mismatch",),
            )
            return
        except ServiceError as error:
            reporter.advance(-sent[0])
            if error.code != "piece_mismatch" or attempt == 2:
                raise


def _start(client, import_id, reporter, sleep, clock) -> None:
    deadline = clock() + BUSY_WAIT_MINUTES * 60
    while True:
        try:
            client.request("POST", f"/v1/imports/{import_id}/start", never_retry=("service_busy",))
            return
        except ServiceError as error:
            if error.code != "service_busy":
                raise
            if clock() >= deadline:
                raise ServiceError(503, "service_busy", "the service stayed busy") from error
            reporter.message("Waiting for a free place on the service…")
            sleep(BUSY_POLL_SECONDS)


def _watch(client, import_id, package, reporter, sleep) -> Entry:
    model, commit = package.model_id, package.commit
    step, done = None, 0
    while True:
        state = client.request("GET", f"/v1/imports/{import_id}").json()
        progress = state.get("progress") or {}
        if progress.get("step") and progress["step"] != step:
            step, done = progress["step"], 0
            reporter.start(f"Service: {step}", total_bytes=progress.get("bytesTotal"))
        if progress.get("bytesDone") is not None:
            reporter.advance(max(0, progress["bytesDone"] - done))
            done = max(done, progress["bytesDone"])
        else:
            reporter.tick()
        if state["state"] in DONE_STATES:
            reporter.finish()
            return _entry_from(state, model, commit)
        sleep(POLL_SECONDS)


def _entry_from(state: dict, model: str, commit: str) -> Entry:
    outcome = state.get("outcome")
    if state["state"] == "done" and outcome == "imported":
        return Entry(model, commit, "imported")
    if state["state"] == "done" and outcome == "completed":
        note = (
            "files were already in Artifactory; record completed"
            if state.get("plan") == "finish"
            else "files uploaded again; record kept"
        )
        return Entry(model, commit, "completed", note)
    if state["state"] == "skipped":
        return Entry(model, commit, "skipped", "already imported")
    error = state.get("error") or {}
    reason = error.get("message") or "the import did not finish"
    return Entry(model, commit, "failed", redact.redact(reason), error.get("code"))


def run(
    client: ServiceClient,
    descriptions: list[Path],
    reporter=None,
    sleep: Callable[[float], None] | None = None,
    clock: Callable[[], float] | None = None,
    on_start: Callable[[str], None] | None = None,
) -> RunReport:
    """Import each bundle in turn; a failure never stops the rest. RunStopped ends the run."""
    reporter = reporter or NullReporter()
    report = RunReport()
    labels = [_label(d) for d in descriptions]
    for position, description in enumerate(descriptions):
        label = labels[position]
        if on_start:
            on_start(label)
        try:
            try:
                package = prepare(description, reporter)
            except PackageFailed as error:
                report.entries.append(
                    Entry(label, "", "failed", redact.redact(error.reason), error.code)
                )
                continue
            report.entries.append(send_package(client, package, reporter, sleep, clock))
        except KeyboardInterrupt:
            raise Interrupted(report, labels[position:]) from None
    return report


def _label(description: Path) -> str:
    name = description.name
    return name.removesuffix(".bundle.json")
