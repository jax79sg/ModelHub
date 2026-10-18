"""The Catalog's HTTP interface (contracts C2 and C3).

Reads need a signed-in person. Writes, removal, the retention list and token checking need the
import service's own identity (rule BR1.14). Documents are served as data (rule BR1.11).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable

import psycopg
import psycopg_pool
from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from modelhub_common.guard import (
    ApiError,
    current_person,
    install_guard,
    require_admin,
    require_client,
)
from modelhub_common.health import HealthCheck, HealthRegistry
from modelhub_common.keys import KeySet
from modelhub_common.tokens import TokenVerifier, Verdict

from .records import InvalidRecord
from .store import (
    CatalogStore,
    Document,
    DocumentGone,
    InvalidQuery,
    InvalidTokenRequest,
    RecordConflict,
    StoreFailed,
    TooManyTokens,
)

SERVICE_CLIENT = "modelhub-artifactory-service"
log = logging.getLogger("modelhub.catalog")
UNSAFE_TYPES = (
    "text/html",
    "image/svg",
    "application/xhtml",
    "text/xml",
    "application/xml",
    "text/javascript",
    "application/javascript",
)
require_service = require_client(SERVICE_CLIENT)


def _err(status: int, code: str, message: str) -> ApiError:
    return ApiError(status, {"code": code, "message": message})


def require_person(person: Verdict = Depends(current_person)) -> Verdict:
    if person.client_id is not None:
        raise _err(403, "forbidden", "A service identity cannot do this.")
    return person


def _served_type(content_type: str) -> str:
    low = (content_type or "").lower()
    if any(low.startswith(t) for t in UNSAFE_TYPES):
        return "application/octet-stream"
    return content_type or "application/octet-stream"


def create_app(
    store: CatalogStore,
    jwks_fetch: Callable[[], dict],
    issuer: str,
    audience: str = "modelhub",
) -> FastAPI:
    keys = KeySet(jwks_fetch)
    keys.load()
    verifier = TokenVerifier(keys, issuer=issuer, audience=audience)
    registry = HealthRegistry([HealthCheck("database", store.ping, critical=True)])
    app = FastAPI(title="modelhub Catalog", docs_url=None, redoc_url=None, openapi_url=None)
    install_guard(app, verifier, "catalog", registry, keys)

    @app.exception_handler(psycopg.OperationalError)
    @app.exception_handler(psycopg_pool.PoolTimeout)
    async def database_unreachable(request: Request, exc: Exception):
        # The database is away: stay up, answer 503, and come back when it does (NFR4.3).
        log.warning("database unreachable", extra={"error": type(exc).__name__})
        return JSONResponse(
            {"code": "database_unavailable", "message": "The database is not reachable."},
            status_code=503,
        )

    # --------------------------------------------------------------------------- models ---
    @app.get("/v1/models")
    def models(request: Request, person: Verdict = Depends(current_person)):
        try:
            return store.list_models(dict(request.query_params))
        except InvalidQuery as exc:
            raise _err(422, "invalid_query", exc.message) from exc

    @app.get("/v1/models/{org}/{name}")
    def model(org: str, name: str, person: Verdict = Depends(current_person)):
        found = store.get_model(f"{org}/{name}")
        if found is None:
            raise _err(404, "not_found", "No such model.")
        return found

    @app.get("/v1/models/{org}/{name}/versions/{commit}")
    def version(org: str, name: str, commit: str, person: Verdict = Depends(current_person)):
        found = store.get_version(f"{org}/{name}", commit)
        if found is None:
            raise _err(404, "not_found", "No such version.")
        return found

    @app.put("/v1/models/{org}/{name}/versions/{commit}")
    async def put_version(
        org: str,
        name: str,
        commit: str,
        record: str = Form(...),
        documents: list[UploadFile] = File(default=[]),
        person: Verdict = Depends(require_service),
    ):
        model_id = f"{org}/{name}"
        try:
            parsed = json.loads(record)
        except ValueError as exc:
            raise _err(422, "invalid_record", "record: not valid JSON") from exc
        docs = []
        for upload in documents:
            kind, _, doc_name = (upload.filename or "").partition("/")
            docs.append(Document(kind, doc_name, upload.content_type or "", await upload.read()))
        try:
            if "version" not in parsed:
                store.put_import_only(model_id, commit, parsed)
                status = "recorded"
            else:
                status = store.put_version(model_id, commit, parsed, docs).status
        except InvalidRecord as exc:
            raise _err(422, "invalid_record", f"{exc.field}: {exc.message}") from exc
        except RecordConflict as exc:
            log.warning("record conflict", extra={"event": "record_conflict", "model": model_id})
            raise _err(
                409, "record_conflict", "A different record exists for this version."
            ) from exc
        except StoreFailed as exc:
            log.error("store failed", extra={"event": "store_failed", "model": model_id})
            raise _err(500, "store_failed", "The version could not be stored.") from exc
        if status == "unchanged":
            return JSONResponse({"status": "unchanged"}, status_code=200)
        return JSONResponse({"status": status}, status_code=201)

    @app.get("/v1/models/{org}/{name}/versions/{commit}/documents/{kind}/{docname:path}")
    def document(
        org: str,
        name: str,
        commit: str,
        kind: str,
        docname: str,
        person: Verdict = Depends(current_person),
    ):
        try:
            found = store.get_document(f"{org}/{name}", commit, kind, docname)
        except DocumentGone as exc:
            raise _err(
                410, "gone", "This version was removed; its documents are no longer stored."
            ) from exc
        if found is None:
            raise _err(404, "not_found", "No such document.")
        data, content_type = found
        return Response(
            data,
            media_type=_served_type(content_type),
            headers={
                "Content-Disposition": 'attachment; filename="document"',
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "sandbox",
                "Cache-Control": "private, max-age=0",
            },
        )

    @app.post("/v1/models/{org}/{name}/versions/{commit}/removal")
    async def removal(
        org: str,
        name: str,
        commit: str,
        request: Request,
        person: Verdict = Depends(require_service),
    ):
        try:
            body = await request.json()
        except ValueError:
            body = {}
        removed_by = (body or {}).get("removedBy") or person.person_name
        try:
            outcome = store.mark_removed(f"{org}/{name}", commit, removed_by)
        except StoreFailed as exc:
            raise _err(500, "store_failed", "The removal could not be recorded.") from exc
        if outcome != "ok":
            raise _err(409, "conflict", "Already removed, or no such imported version.")
        log.info(
            "version removed",
            extra={
                "event": "version_removed",
                "model": f"{org}/{name}",
                "commit": commit,
                "by": removed_by,
            },
        )
        return {"status": "removed"}

    # ---------------------------------------------------------------- retention, trail ---
    @app.get("/v1/versions")
    def versions(
        state: str | None = None,
        importedBefore: str | None = None,
        page: int = 1,
        pageSize: int = 100,
        person: Verdict = Depends(require_service),
    ):
        try:
            return store.versions_for_retention(state, importedBefore, page, pageSize)
        except InvalidQuery as exc:
            raise _err(422, "invalid_query", exc.message) from exc

    @app.get("/v1/trail")
    def trail(
        model: str | None = None,
        person: str | None = None,
        page: int = 1,
        pageSize: int = 30,
        who: Verdict = Depends(current_person),
    ):
        try:
            return store.trail(model, person, page, pageSize)
        except InvalidQuery as exc:
            raise _err(422, "invalid_query", exc.message) from exc

    # ------------------------------------------------------------------------- tokens ---
    @app.post("/v1/tokens")
    async def make_token(request: Request, person: Verdict = Depends(require_person)):
        body = await request.json()
        try:
            made = store.make_token(person.person_id, person.person_name, (body or {}).get("name"))
        except InvalidTokenRequest as exc:
            raise _err(422, "invalid_token_request", str(exc)) from exc
        except TooManyTokens as exc:
            raise _err(422, "too_many_tokens", "Revoke an unused token first.") from exc
        log.info("token made", extra={"event": "token_made", "person": person.person_name})
        return JSONResponse(made, status_code=201)

    @app.get("/v1/tokens")
    def list_tokens(all: bool = False, person: Verdict = Depends(require_person)):
        if all and person.is_admin:
            return {"items": store.list_tokens(None)}
        return {"items": store.list_tokens(person.person_id)}

    @app.delete("/v1/tokens/{token_id}")
    def revoke(token_id: str, person: Verdict = Depends(require_person)):
        if not store.revoke_token(token_id, person.person_id, person.is_admin):
            raise _err(404, "not_found", "No such token.")
        log.info("token revoked", extra={"event": "token_revoked", "person": person.person_name})
        return Response(status_code=204)

    @app.post("/v1/tokens/introspect")
    async def introspect(request: Request, person: Verdict = Depends(require_service)):
        body = await request.json()
        return store.introspect((body or {}).get("token", ""))

    @app.get("/v1/settings/token-lifetime")
    def get_lifetime(person: Verdict = Depends(current_person)):
        return {"days": store.token_lifetime_days()}

    @app.put("/v1/settings/token-lifetime")
    async def set_lifetime(request: Request, person: Verdict = Depends(require_admin)):
        body = await request.json()
        try:
            days = store.set_token_lifetime_days((body or {}).get("days"), person.person_name)
        except InvalidQuery as exc:
            raise _err(422, "invalid_query", exc.message) from exc
        return {"days": days}

    return app
