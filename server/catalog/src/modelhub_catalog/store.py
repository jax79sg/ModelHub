"""The Catalog's database access (rules BR1.1 to BR1.20).

Plain SQL with bound parameters only; the sort field is chosen from a fixed list, never from text.
The models list reads the ``model_summary`` table alone and never the documents (NFR2.2).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from .records import (
    Document,
    InvalidRecord,
    Validated,
    checksum,
    parse_time,
    validate_import_only,
    validate_record,
)

__all__ = ["CatalogStore", "Document", "InvalidRecord"]

LIST_SQL_TABLES = ("model_summary",)
TOKEN_PREFIX = "mhi_"
MAX_ACTIVE_TOKENS = 20
LAST_USED_MINUTES = 1
SORTS = {
    "downloads": "downloads desc nulls last",
    "likes": "likes desc nulls last",
    "lastModified": "last_modified_at desc nulls last",
    "createdAt": "created_at desc nulls last",
    "importedAt": "imported_at desc",
    "name": "model_key asc",
}
BANDS = {
    "lt1b": ("parameter_count < %s", [1_000_000_000]),
    "6b": ("parameter_count >= %s and parameter_count < %s", [1_000_000_000, 6_000_000_000]),
    "12b": ("parameter_count >= %s and parameter_count < %s", [6_000_000_000, 12_000_000_000]),
    "32b": ("parameter_count >= %s and parameter_count < %s", [12_000_000_000, 32_000_000_000]),
    "128b": ("parameter_count >= %s and parameter_count < %s", [32_000_000_000, 128_000_000_000]),
    "gt500b": ("parameter_count > %s", [500_000_000_000]),
}
_LIKE_ESCAPE = str.maketrans({"\\": "\\\\", "%": "\\%", "_": "\\_"})


class RecordConflict(Exception):
    """A different record already exists for this model and commit."""


class StoreFailed(Exception):
    """The database refused part of a store; nothing was kept."""


class InvalidQuery(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DocumentGone(Exception):
    """The version was removed and its documents' content deleted."""


class TooManyTokens(Exception):
    pass


class InvalidTokenRequest(Exception):
    pass


@dataclass
class PutResult:
    status: str  # created | unchanged | reinstated | recorded


def _iso(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return value


def _clean(row: dict) -> dict:
    return {k: _iso(v) for k, v in row.items()}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _int_param(q: dict, name: str, default: int, low: int, high: int | None) -> int:
    raw = q.get(name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise InvalidQuery(f"{name} must be a whole number") from None
    if value < low:
        raise InvalidQuery(f"{name} must be at least {low}")
    return min(value, high) if high else value


def _flag(value) -> bool:
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes", "on")
    return bool(value)


class CatalogStore:
    def __init__(
        self,
        url: str,
        pepper: bytes,
        clock: Callable[[], datetime] = _utc_now,
        pool_size: int = 10,
        statement_timeout_ms: int = 5000,
    ) -> None:
        self._pepper = pepper
        self._clock = clock
        self._pool = ConnectionPool(
            url,
            min_size=1,
            max_size=pool_size,
            timeout=5,
            kwargs={
                "row_factory": dict_row,
                "options": f"-c statement_timeout={statement_timeout_ms} -c timezone=UTC",
            },
            open=True,
        )

    def close(self) -> None:
        self._pool.close()

    def ping(self) -> bool:
        with self._pool.connection() as conn:
            conn.execute("select 1")
        return True

    # ------------------------------------------------------------------ storing a version ---
    def put_version(
        self, model_id: str, commit: str, record: dict, documents: list[Document]
    ) -> PutResult:
        v = validate_record(model_id, commit, record, documents)
        digest = checksum(v)
        key = model_id.lower()
        try:
            with self._pool.connection() as conn, conn.transaction():
                conn.execute("select pg_advisory_xact_lock(hashtext(%s))", (key + "@" + commit,))
                existing = conn.execute(
                    "select state, record_checksum from model_versions "
                    "where model_key = %s and commit = %s",
                    (key, commit),
                ).fetchone()
                if existing and existing["state"] == "imported":
                    if existing["record_checksum"] == digest:
                        return PutResult("unchanged")
                    raise RecordConflict(f"{model_id}@{commit}")
                reinstate = existing is not None  # a removed version comes back
                self._write(conn, key, v, digest, reinstate)
                self._refresh_summary(conn, key)
                return PutResult("reinstated" if reinstate else "created")
        except psycopg.Error as exc:
            raise StoreFailed(type(exc).__name__) from exc

    def _write(self, conn, key: str, v: Validated, digest: str, reinstate: bool) -> None:
        ver, imp = v.version, v.import_record
        conn.execute(
            "insert into models(model_key, model_id, first_imported_at) values (%s, %s, %s) "
            "on conflict (model_key) do nothing",
            (key, v.model_id, imp["imported_at"]),
        )
        cols = (
            "captured_at",
            "license",
            "language",
            "tags",
            "task",
            "library",
            "parameter_count",
            "downloads",
            "likes",
            "size_bytes",
            "counts_captured_at",
            "created_at",
            "last_modified_at",
        )
        values = [ver[c] for c in cols]
        common = (
            v.has_readme,
            v.card_text,
            digest,
            1,
            imp["imported_at"],
            imp["imported_by_id"],
            imp["imported_by_name"],
        )
        if reinstate:
            conn.execute(
                "delete from documents where model_key = %s and commit = %s", (key, v.commit)
            )
            conn.execute(
                "delete from version_files where model_key = %s and commit = %s", (key, v.commit)
            )
            sets = ", ".join(f"{c} = %s" for c in cols)
            conn.execute(
                f"update model_versions set state = 'imported', removed_at = null, "  # noqa: S608
                f"removed_by = null, {sets}, has_readme = %s, card_text = %s, record_checksum = %s, "
                "record_format = %s, imported_at = %s, imported_by_id = %s, imported_by_name = %s "
                "where model_key = %s and commit = %s",
                [*values, *common, key, v.commit],
            )
        else:
            names = ", ".join(cols)
            marks = ", ".join(["%s"] * len(cols))
            conn.execute(
                f"insert into model_versions (model_key, commit, {names}, has_readme, card_text, "  # noqa: S608
                "record_checksum, record_format, imported_at, imported_by_id, imported_by_name) "
                f"values (%s, %s, {marks}, %s, %s, %s, %s, %s, %s, %s)",
                [key, v.commit, *values, *common],
            )
        with conn.cursor() as cur:
            cur.executemany(
                "insert into version_files (model_key, commit, path, size_bytes, sha256, file_type, "
                "safety_scan, downloaded) values (%s, %s, %s, %s, %s, %s, %s, %s)",
                [
                    (
                        key,
                        v.commit,
                        f["path"],
                        f["size_bytes"],
                        f["sha256"],
                        f["file_type"],
                        f["safety_scan"],
                        f["downloaded"],
                    )
                    for f in v.files
                ],
            )
            cur.executemany(
                "insert into refs (model_key, kind, name, commit) values (%s, %s, %s, %s) "
                "on conflict (model_key, kind, name) do update set commit = excluded.commit",
                [(key, r["kind"], r["name"], r["commit"]) for r in v.refs],
            )
            cur.executemany(
                "insert into documents (model_key, commit, kind, name, content_type, size_bytes, "
                "sha256, content, picture_status) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [
                    (
                        key,
                        v.commit,
                        d.kind,
                        d.name,
                        d.content_type,
                        len(d.content),
                        d.sha256,
                        d.content,
                        d.picture_status,
                    )
                    for d in v.documents
                ],
            )
        self._insert_trail(conn, key, v.model_id, v.commit, imp)

    @staticmethod
    def _insert_trail(conn, key: str, model_id: str, commit: str, imp: dict) -> None:
        conn.execute(
            "insert into import_records (record_id, model_key, model_id, commit, imported_by_id, "
            "imported_by_name, imported_at, computer, bundle_name, bundle_sha256, "
            "signing_key_fingerprint, tool_version, check_results, outcome) "
            "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                uuid.uuid4(),
                key,
                model_id,
                commit,
                imp["imported_by_id"],
                imp["imported_by_name"],
                imp["imported_at"],
                imp["computer"],
                imp["bundle_name"],
                imp["bundle_sha256"],
                imp["signing_key_fingerprint"],
                imp["tool_version"],
                Jsonb(imp["check_results"]),
                imp["outcome"],
            ),
        )

    def put_import_only(self, model_id: str, commit: str, record: dict) -> PutResult:
        imp = validate_import_only(model_id, commit, record)
        key = model_id.lower()
        try:
            with self._pool.connection() as conn, conn.transaction():
                row = conn.execute(
                    "select state from model_versions where model_key = %s and commit = %s",
                    (key, commit),
                ).fetchone()
                if row is None or row["state"] != "imported":
                    raise InvalidRecord("version", "no imported version to record against")
                self._insert_trail(conn, key, model_id, commit, imp)
        except psycopg.Error as exc:
            raise StoreFailed(type(exc).__name__) from exc
        return PutResult("recorded")

    def _refresh_summary(self, conn, key: str) -> None:
        """Set the model's summary row from its latest imported version (rule BR1.7)."""
        latest = conn.execute(
            "select v.*, m.model_id from model_versions v join models m using (model_key) "
            "where v.model_key = %s and v.state = 'imported' "
            "order by v.imported_at desc, v.commit desc limit 1",
            (key,),
        ).fetchone()
        if latest is None:
            conn.execute(
                "update model_summary set state = 'removed', search_vector = null "
                "where model_key = %s",
                (key,),
            )
            return
        tags = latest["tags"] or []
        ids_text = latest["model_id"] + " " + " ".join(tags)
        conn.execute(
            "insert into model_summary (model_key, model_id, latest_commit, state, task, library, "
            "license, language, parameter_count, downloads, likes, last_modified_at, created_at, "
            "imported_at, imported_by_id, imported_by_name, tags, ids_text, search_vector) "
            "values (%(k)s, %(mid)s, %(c)s, 'imported', %(task)s, %(lib)s, %(lic)s, %(lang)s, "
            "%(pc)s, %(dl)s, %(lk)s, %(lm)s, %(cr)s, %(ia)s, %(ib)s, %(ibn)s, %(tags)s, %(ids)s, "
            "to_tsvector('english', coalesce(%(card)s, ''))) "
            "on conflict (model_key) do update set latest_commit = excluded.latest_commit, "
            "state = 'imported', task = excluded.task, library = excluded.library, "
            "license = excluded.license, language = excluded.language, "
            "parameter_count = excluded.parameter_count, downloads = excluded.downloads, "
            "likes = excluded.likes, last_modified_at = excluded.last_modified_at, "
            "created_at = excluded.created_at, imported_at = excluded.imported_at, "
            "imported_by_id = excluded.imported_by_id, imported_by_name = excluded.imported_by_name, "
            "tags = excluded.tags, ids_text = excluded.ids_text, "
            "search_vector = excluded.search_vector",
            {
                "k": key,
                "mid": latest["model_id"],
                "c": latest["commit"],
                "task": latest["task"],
                "lib": latest["library"],
                "lic": latest["license"],
                "lang": latest["language"],
                "pc": latest["parameter_count"],
                "dl": latest["downloads"],
                "lk": latest["likes"],
                "lm": latest["last_modified_at"],
                "cr": latest["created_at"],
                "ia": latest["imported_at"],
                "ib": latest["imported_by_id"],
                "ibn": latest["imported_by_name"],
                "tags": tags,
                "ids": ids_text,
                "card": latest["card_text"],
            },
        )

    # -------------------------------------------------------------------------- the list ---
    def list_models(self, q: dict) -> dict:
        page = _int_param(q, "page", 1, 1, None)
        size = _int_param(q, "pageSize", 30, 1, 100)
        sort = q.get("sort") or "downloads"
        if sort not in SORTS:
            raise InvalidQuery(f"sort must be one of {sorted(SORTS)}")
        where: list[str] = []
        params: list = []
        if not _flag(q.get("showRemoved")):
            where.append("state = 'imported'")
        for name, column in (
            ("task", "task"),
            ("library", "library"),
            ("license", "license"),
            ("importedBy", "imported_by_id"),
        ):
            if q.get(name):
                where.append(f"{column} = %s")
                params.append(q[name])
        if q.get("language"):
            where.append("%s = any(language)")
            params.append(q["language"])
        if q.get("parameters"):
            band = BANDS.get(q["parameters"])
            if band is None:
                raise InvalidQuery(f"parameters must be one of {sorted(BANDS)}")
            where.append(band[0])
            params.extend(band[1])
        for name, op in (("importedFrom", ">="), ("importedTo", "<=")):
            if q.get(name):
                try:
                    when = parse_time(q[name], name)
                except InvalidRecord:
                    raise InvalidQuery(f"{name} must be a UTC time") from None
                where.append(f"imported_at {op} %s")
                params.append(when)
        rank_sql, rank_params = "", []
        text = (q.get("q") or "").strip()
        if text:
            if len(text) > 200:
                raise InvalidQuery("q is at most 200 characters")
            words = text.split()
            if len(words) > 10 or any(len(w) > 100 for w in words):
                raise InvalidQuery("q is at most 10 words of at most 100 characters")
            for word in words:
                like = "%" + word.translate(_LIKE_ESCAPE) + "%"
                where.append(
                    "(search_vector @@ plainto_tsquery('english', %s) "
                    "or (char_length(%s) >= 3 and ids_text ilike %s))"
                )
                params.extend([word, word, like])
            rank_sql = "ts_rank(search_vector, plainto_tsquery('english', %s)) desc nulls last, "
            rank_params = [text]
        clause = (" where " + " and ".join(where)) if where else ""
        base = "from model_summary" + clause  # the list reads this table only
        with self._pool.connection() as conn:
            total = conn.execute("select count(*) as n " + base, params).fetchone()["n"]
            rows = conn.execute(
                "select model_id, latest_commit, state, task, library, license, language, "
                "parameter_count, downloads, likes, last_modified_at, created_at, imported_at, "
                "imported_by_id, imported_by_name, tags "
                + base
                + f" order by {rank_sql}{SORTS[sort]}, model_key limit %s offset %s",  # noqa: S608
                [*params, *rank_params, size, (page - 1) * size],
            ).fetchall()
            facets = self._facets(conn, base, params)
        return {
            "items": [_clean(r) for r in rows],
            "total": total,
            "page": page,
            "pageSize": size,
            "facets": facets,
        }

    @staticmethod
    def _facets(conn, base: str, params: list) -> dict:
        out: dict[str, dict] = {}
        for name, column in (
            ("task", "task"),
            ("library", "library"),
            ("license", "license"),
            ("importedBy", "imported_by_name"),
        ):
            rows = conn.execute(
                f"select {column} as v, count(*) as n from (select * {base}) s "  # noqa: S608
                f"where {column} is not null group by {column} order by count(*) desc, {column}",
                params,
            ).fetchall()
            out[name] = {r["v"]: r["n"] for r in rows}
        rows = conn.execute(
            f"select l as v, count(*) as n from (select unnest(language) as l {base}) s "  # noqa: S608
            "group by l order by count(*) desc, l",
            params,
        ).fetchall()
        out["language"] = {r["v"]: r["n"] for r in rows}
        return out

    # -------------------------------------------------------------- reading one thing ---
    def get_model(self, model_id: str) -> dict | None:
        key = model_id.lower()
        with self._pool.connection() as conn:
            model = conn.execute(
                "select model_id, first_imported_at from models where model_key = %s", (key,)
            ).fetchone()
            if model is None:
                return None
            versions = conn.execute(
                "select commit, state, imported_at, imported_by_name, size_bytes "
                "from model_versions where model_key = %s order by imported_at desc, commit",
                (key,),
            ).fetchall()
            refs = conn.execute(
                "select kind, name, commit from refs where model_key = %s order by kind, name",
                (key,),
            ).fetchall()
        return {
            **_clean(model),
            "versions": [_clean(v) for v in versions],
            "refs": [dict(r) for r in refs],
        }

    def get_version(self, model_id: str, commit: str) -> dict | None:
        key = model_id.lower()
        with self._pool.connection() as conn:
            v = conn.execute(
                "select v.*, m.model_id from model_versions v join models m using (model_key) "
                "where v.model_key = %s and v.commit = %s",
                (key, commit),
            ).fetchone()
            if v is None:
                return None
            files = conn.execute(
                "select path, size_bytes, sha256, file_type, safety_scan, downloaded "
                "from version_files where model_key = %s and commit = %s order by path",
                (key, commit),
            ).fetchall()
            docs = conn.execute(
                "select kind, name, content_type, size_bytes, sha256, picture_status "
                "from documents where model_key = %s and commit = %s order by kind, name",
                (key, commit),
            ).fetchall()
        v = _clean(v)
        for internal in ("model_key", "card_text", "record_checksum", "record_format"):
            v.pop(internal, None)
        v["files"] = [dict(f) for f in files]
        v["documents"] = [dict(d) for d in docs]
        return v

    def get_document(self, model_id: str, commit: str, kind: str, name: str):
        key = model_id.lower()
        with self._pool.connection() as conn:
            row = conn.execute(
                "select d.content, d.content_type, v.state from documents d "
                "join model_versions v on v.model_key = d.model_key and v.commit = d.commit "
                "where d.model_key = %s and d.commit = %s and d.kind = %s and d.name = %s",
                (key, commit, kind, name),
            ).fetchone()
        if row is None:
            return None
        if row["state"] == "removed" or row["content"] is None:
            raise DocumentGone(f"{kind}/{name}")
        return bytes(row["content"]), row["content_type"]

    # ----------------------------------------------------------------------- removal ---
    def mark_removed(self, model_id: str, commit: str, removed_by: str) -> str:
        key = model_id.lower()
        try:
            with self._pool.connection() as conn, conn.transaction():
                conn.execute("select pg_advisory_xact_lock(hashtext(%s))", (key + "@" + commit,))
                row = conn.execute(
                    "select state from model_versions where model_key = %s and commit = %s",
                    (key, commit),
                ).fetchone()
                if row is None or row["state"] != "imported":
                    return "conflict"
                conn.execute(
                    "update model_versions set state = 'removed', removed_at = %s, removed_by = %s, "
                    "card_text = null where model_key = %s and commit = %s",
                    (self._clock(), removed_by, key, commit),
                )
                conn.execute(
                    "update documents set content = null where model_key = %s and commit = %s",
                    (key, commit),
                )
                self._refresh_summary(conn, key)
                return "ok"
        except psycopg.Error as exc:
            raise StoreFailed(type(exc).__name__) from exc

    # ------------------------------------------------------------ trail and retention ---
    def trail(
        self,
        model_id: str | None = None,
        person_id: str | None = None,
        page: int = 1,
        page_size: int = 30,
    ) -> dict:
        page = _int_param({"page": page}, "page", 1, 1, None)
        size = _int_param({"pageSize": page_size}, "pageSize", 30, 1, 100)
        where, params = [], []
        if model_id:
            where.append("model_key = %s")
            params.append(model_id.lower())
        if person_id:
            where.append("imported_by_id = %s")
            params.append(person_id)
        clause = (" where " + " and ".join(where)) if where else ""
        with self._pool.connection() as conn:
            total = conn.execute(
                "select count(*) as n from import_records" + clause, params
            ).fetchone()["n"]
            rows = conn.execute(
                "select record_id::text as record_id, model_id, commit, imported_by_id, "
                "imported_by_name, imported_at, computer, bundle_name, bundle_sha256, "
                "signing_key_fingerprint, tool_version, check_results, outcome "
                "from import_records"
                + clause
                + " order by imported_at desc, record_id limit %s offset %s",
                [*params, size, (page - 1) * size],
            ).fetchall()
        return {"items": [_clean(r) for r in rows], "total": total, "page": page, "pageSize": size}

    def versions_for_retention(
        self,
        state: str | None = None,
        imported_before: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        if state not in (None, "imported", "removed"):
            raise InvalidQuery("state must be imported or removed")
        page = _int_param({"page": page}, "page", 1, 1, None)
        size = _int_param({"pageSize": page_size}, "pageSize", 100, 1, 1000)
        where, params = [], []
        if state:
            where.append("v.state = %s")
            params.append(state)
        if imported_before:
            try:
                params.append(parse_time(imported_before, "importedBefore"))
            except InvalidRecord:
                raise InvalidQuery("importedBefore must be a UTC time") from None
            where.append("v.imported_at < %s")
        clause = (" where " + " and ".join(where)) if where else ""
        with self._pool.connection() as conn:
            rows = conn.execute(
                "select m.model_id, v.commit, v.imported_at, v.imported_by_name as imported_by, "
                "v.size_bytes from model_versions v join models m using (model_key)"
                + clause
                + " order by v.imported_at asc, v.commit limit %s offset %s",
                [*params, size, (page - 1) * size],
            ).fetchall()
        items = []
        for r in rows:
            r = _clean(r)
            items.append({"versionKey": f"{r['model_id']}@{r['commit']}", **r})
        return {"items": items, "page": page, "pageSize": size}

    # --------------------------------------------------------------- personal tokens ---
    def _hash(self, value: str) -> str:
        return hmac.new(self._pepper, value.encode(), hashlib.sha256).hexdigest()

    def token_lifetime_days(self) -> int:
        with self._pool.connection() as conn:
            row = conn.execute(
                "select value from catalog_settings where key = 'token_lifetime_days'"
            ).fetchone()
        return row["value"]

    def set_token_lifetime_days(self, days, changed_by: str) -> int:
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365:
            raise InvalidQuery("the token lifetime must be 1 to 365 days")
        with self._pool.connection() as conn:
            conn.execute(
                "update catalog_settings set value = %s, changed_by = %s, changed_at = %s "
                "where key = 'token_lifetime_days'",
                (days, changed_by, self._clock()),
            )
        return days

    def make_token(self, owner_id: str, owner_name: str, name: str) -> dict:
        name = (name or "").strip()
        if not 1 <= len(name) <= 60:
            raise InvalidTokenRequest("the name must be 1 to 60 characters")
        now = self._clock()
        lifetime = self.token_lifetime_days()
        value = TOKEN_PREFIX + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip(
            "="
        )
        token_id = uuid.uuid4().hex
        with self._pool.connection() as conn, conn.transaction():
            conn.execute("select pg_advisory_xact_lock(hashtext(%s))", ("tokens:" + owner_id,))
            active = conn.execute(
                "select count(*) as n from personal_tokens where owner_id = %s "
                "and revoked_at is null and expires_at > %s",
                (owner_id, now),
            ).fetchone()["n"]
            if active >= MAX_ACTIVE_TOKENS:
                raise TooManyTokens(owner_id)
            conn.execute(
                "insert into personal_tokens (token_id, owner_id, owner_name, name, prefix, "
                "value_hash, created_at, expires_at) values (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    token_id,
                    owner_id,
                    owner_name,
                    name,
                    value[:8],
                    self._hash(value),
                    now,
                    now + timedelta(days=lifetime),
                ),
            )
        return {
            "tokenId": token_id,
            "token": value,
            "scope": "import",
            "expiresAt": _iso(now + timedelta(days=lifetime)),
        }

    def list_tokens(self, owner_id: str | None) -> list[dict]:
        where, params = ("where owner_id = %s", [owner_id]) if owner_id else ("", [])
        with self._pool.connection() as conn:
            rows = conn.execute(
                "select token_id, owner_id, owner_name, name, prefix, created_at, expires_at, "
                f"last_used_at, revoked_at from personal_tokens {where} "  # noqa: S608
                "order by created_at desc, token_id",
                params,
            ).fetchall()
        return [_clean(r) for r in rows]

    def revoke_token(self, token_id: str, caller_id: str, is_admin: bool) -> bool:
        """True when the caller may see the token (owner or administrator); repeats are fine."""
        with self._pool.connection() as conn, conn.transaction():
            row = conn.execute(
                "select owner_id, revoked_at from personal_tokens where token_id = %s", (token_id,)
            ).fetchone()
            if row is None or (row["owner_id"] != caller_id and not is_admin):
                return False
            if row["revoked_at"] is None:
                conn.execute(
                    "update personal_tokens set revoked_at = %s, revoked_by = %s where token_id = %s",
                    (self._clock(), caller_id, token_id),
                )
        return True

    def introspect(self, value: str) -> dict:
        if not value or not value.startswith(TOKEN_PREFIX):
            return {"active": False, "reason": "unknown"}
        now = self._clock()
        with self._pool.connection() as conn, conn.transaction():
            row = conn.execute(
                "select token_id, owner_id, owner_name, expires_at, revoked_at, last_used_at "
                "from personal_tokens where value_hash = %s",
                (self._hash(value),),
            ).fetchone()
            if row is None:
                return {"active": False, "reason": "unknown"}
            if row["revoked_at"] is not None:
                return {"active": False, "reason": "revoked"}
            if row["expires_at"] <= now:
                return {"active": False, "reason": "expired"}
            last = row["last_used_at"]
            if last is None or now - last >= timedelta(minutes=LAST_USED_MINUTES):
                conn.execute(
                    "update personal_tokens set last_used_at = %s where token_id = %s",
                    (now, row["token_id"]),
                )
        return {
            "active": True,
            "ownerId": row["owner_id"],
            "ownerName": row["owner_name"],
            "scope": "import",
        }
