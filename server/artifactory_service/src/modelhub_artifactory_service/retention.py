"""Retention: the period, the list of versions due, and keep or remove decisions (BR1.10, BR1.15-BR1.18).

Removing is two steps in a fixed order: delete the files in Artifactory, then mark the version
removed in the Catalog. A failure at either step leaves the version listed, and a repeat of the
decision does only what is still left to do.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from modelhub_artifactory_service.catalog_client import (
    AuthUnavailable,
    CatalogUnavailable,
)
from modelhub_artifactory_service.gateway import ArtifactoryUnreachable, UploadError

log = logging.getLogger("modelhub.retention")


class RetentionError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class Retention:
    def __init__(self, pool, gateway, catalog, clock=_utc_now) -> None:
        self.pool, self.gateway, self.catalog, self.clock = pool, gateway, catalog, clock

    # -- the period ---------------------------------------------------------------------------
    def settings(self) -> dict:
        with self.pool.connection() as conn:
            row = conn.execute("select * from retention_settings where id = 1").fetchone()
        return {
            "periodDays": row["retention_days"],
            "changedBy": row["changed_by_name"],
            "changedAt": _iso(row["changed_at"]) if row["changed_at"] else None,
        }

    def set_period(self, days, by_name: str) -> dict:
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 3650:
            raise RetentionError(
                422, "invalid_period", "The period is a whole number of days, 1 to 3650."
            )
        with self.pool.connection() as conn:
            conn.execute(
                "update retention_settings set retention_days = %s, changed_by_name = %s, "
                "changed_at = %s where id = 1",
                (days, by_name, self.clock()),
            )
        return self.settings()

    # -- the list -----------------------------------------------------------------------------
    def due(self) -> list[dict]:
        now = self.clock()
        cutoff = now - timedelta(days=self.settings()["periodDays"])
        kept = self._last_keeps()
        found, page = [], 1
        while True:
            body = self.catalog.versions("imported", _iso(cutoff), page, 500)
            for item in body["items"]:
                keep = kept.get((item["model_id"], item["commit"]))
                if keep and keep > cutoff:
                    continue
                imported = _parse(item["imported_at"])
                found.append(
                    {
                        "modelId": item["model_id"],
                        "commit": item["commit"],
                        "importedAt": _iso(imported),
                        "importedBy": item.get("imported_by"),
                        "sizeBytes": item.get("size_bytes"),
                        "ageDays": (now - imported).days,
                        "lastKeptAt": _iso(keep) if keep else None,
                    }
                )
            if len(body["items"]) < body["pageSize"]:
                return found
            page += 1

    def _last_keeps(self) -> dict:
        with self.pool.connection() as conn:
            rows = conn.execute(
                "select model_id, commit, max(decided_at) as at from retention_decisions "
                "where decision = 'keep' group by model_id, commit"
            ).fetchall()
        return {(r["model_id"], r["commit"]): r["at"] for r in rows}

    # -- decisions ----------------------------------------------------------------------------
    def decisions(self, model: str | None = None, person: str | None = None) -> list[dict]:
        where, params = [], []
        if model:
            where.append("model_id = %s")
            params.append(model)
        if person:
            where.append("decided_by_name = %s")
            params.append(person)
        clause = (" where " + " and ".join(where)) if where else ""
        with self.pool.connection() as conn:
            rows = conn.execute(
                "select * from retention_decisions" + clause + " order by decided_at desc",
                params,
            ).fetchall()
        return [
            {
                "decisionId": r["decision_id"],
                "modelId": r["model_id"],
                "commit": r["commit"],
                "decision": r["decision"],
                "decidedBy": r["decided_by_name"],
                "decidedAt": _iso(r["decided_at"]),
                "outcome": r["outcome"],
                "message": r["failure_message"],
            }
            for r in rows
        ]

    def decide(self, model_id: str, commit: str, decision: str, by_id: str, by_name: str) -> dict:
        if decision not in ("keep", "remove"):
            raise RetentionError(422, "invalid_decision", "The decision is keep or remove.")
        try:
            version = self.catalog.get_version(model_id, commit)
        except (CatalogUnavailable, AuthUnavailable) as exc:
            raise RetentionError(
                503, "catalog_unavailable", "The Catalog could not be reached."
            ) from exc
        if not version or version.get("state") != "imported":
            raise RetentionError(409, "not_removable", "This version is not an imported version.")
        decision_id = uuid.uuid4().hex
        log.info(
            "retention_decided",
            extra={
                "event": "retention_decided",
                "decisionId": decision_id,
                "model": model_id,
                "commit": commit,
                "decision": decision,
                "personId": by_id,
            },
        )
        resume = decision == "remove" and self._files_already_deleted(model_id, commit)
        outcome = "done" if decision == "keep" else "failed"
        self._store(decision_id, model_id, commit, decision, by_id, by_name, outcome, None, None)
        if decision == "keep":
            return {"decisionId": decision_id, "outcome": "kept"}
        return self._remove(decision_id, model_id, commit, by_name, resume)

    def _files_already_deleted(self, model_id: str, commit: str) -> bool:
        with self.pool.connection() as conn:
            row = conn.execute(
                "select outcome from retention_decisions where model_id = %s and commit = %s "
                "and decision = 'remove' order by decided_at desc limit 1",
                (model_id, commit),
            ).fetchone()
        return bool(row and row["outcome"] == "files_deleted_not_marked")

    def _remove(self, decision_id, model_id, commit, by_name, files_gone: bool) -> dict:
        if not files_gone:
            try:
                listing = self.gateway.list_version(model_id, commit)
                self.gateway.delete_version(listing)
            except (ArtifactoryUnreachable, UploadError) as exc:
                message = getattr(exc, "message", None) or str(exc)
                self._update(decision_id, "failed", "artifactory", message)
                return {"decisionId": decision_id, "outcome": "removal_failed", "message": message}
        try:
            result = self.catalog.mark_removed(model_id, commit, by_name)
        except (CatalogUnavailable, AuthUnavailable) as exc:
            result, text = "unavailable", str(exc)
        else:
            text = "The Catalog did not accept the removal."
        if result != "ok":
            self._update(decision_id, "files_deleted_not_marked", "catalog", text)
            return {"decisionId": decision_id, "outcome": "removal_failed", "message": text}
        self._update(decision_id, "done", None, None)
        return {"decisionId": decision_id, "outcome": "removed"}

    def _store(self, decision_id, model_id, commit, decision, by_id, by_name, outcome, code, msg):
        with self.pool.connection() as conn:
            conn.execute(
                "insert into retention_decisions (decision_id, model_id, commit, decision, "
                "decided_by_id, decided_by_name, decided_at, outcome, failure_code, "
                "failure_message) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    decision_id,
                    model_id,
                    commit,
                    decision,
                    by_id,
                    by_name,
                    self.clock(),
                    outcome,
                    code,
                    msg,
                ),
            )

    def _update(self, decision_id: str, outcome: str, code, message) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                "update retention_decisions set outcome = %s, failure_code = %s, "
                "failure_message = %s where decision_id = %s",
                (outcome, code, message, decision_id),
            )
