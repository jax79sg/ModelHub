"""The service's HTTP interface: the import API (C1) and the retention and keys API (C4).

Import calls carry a personal token, which the Catalog checks; they skip the Keycloak check and
do their own (BR1.1). Everything else carries a Keycloak token; changes need an administrator.
"""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from fastapi import Depends, FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from modelhub_common.guard import (
    ApiError,
    current_person,
    install_guard,
    require_admin,
)
from modelhub_common.health import HealthCheck, HealthRegistry
from modelhub_common.keys import KeySet
from modelhub_common.tokens import TokenVerifier, Verdict

from modelhub_artifactory_service.catalog_client import AuthUnavailable, CatalogUnavailable
from modelhub_artifactory_service.importer import MAX_RUNNING, ServiceError
from modelhub_artifactory_service.keys import FingerprintMismatch, InvalidKey, KeyExists
from modelhub_artifactory_service.retention import RetentionError

log = logging.getLogger("modelhub.artifactory_service")
IMPORT_PREFIX = "/v1/imports"
# The contract's words for what the importer calls things inside.
WIRE = {
    "key-untrusted": (422, "untrusted_signing_key"),
    "signature-invalid": (422, "bad_signature"),
    "signature-missing": (422, "bad_signature"),
    "invalid_names": (422, "name_rule_broken"),
    "piece_damaged": (409, "piece_mismatch"),
}


def _version(text: str | None) -> tuple[int, ...] | None:
    try:
        return tuple(int(p) for p in (text or "").strip().split("."))
    except ValueError:
        return None


def _error(status: int, code: str, message: str, retryable: bool = False, **extra) -> ApiError:
    return ApiError(status, {"code": code, "message": message, "retryable": retryable, **extra})


def _wire(exc: ServiceError) -> ApiError:
    status, code = WIRE.get(exc.code, (exc.status, exc.code))
    return _error(status, code, exc.message, exc.retryable)


def _shape(view: dict) -> dict:
    """The contract's Import object from the importer's flat view."""
    out = {
        "importId": view["importId"],
        "state": view["state"],
        "pieceCount": view["pieceCount"],
        "progress": {
            "step": view["step"],
            "bytesDone": view["bytesDone"],
            "bytesTotal": view["bytesTotal"],
            "updatedAt": view["endedAt"] or view["createdAt"],
        },
    }
    if view["outcome"]:
        out["outcome"] = view["outcome"]
    if "missingPieces" in view:
        out["missingPieces"] = view["missingPieces"]
    if view["error"]:
        out["error"] = view["error"]
        out["message"] = view["error"]["message"]
    return out


def create_app(
    importer,
    retention,
    keys,
    catalog,
    jwks_fetch: Callable[[], dict],
    issuer: str,
    audience: str = "modelhub",
    min_client_version: str = "0.0.0",
    runner: Callable[[Callable[[], None]], None] | None = None,
    extra_checks: list[HealthCheck] | None = None,
) -> FastAPI:
    keyset = KeySet(jwks_fetch)
    keyset.load()
    verifier = TokenVerifier(keyset, issuer=issuer, audience=audience)

    def database_ok() -> bool:
        with importer.pool.connection() as conn:
            conn.execute("select 1")
        return True

    registry = HealthRegistry(
        [HealthCheck("database", database_ok, critical=True), *(extra_checks or [])]
    )
    app = FastAPI(
        title="modelhub artifactory-service", docs_url=None, redoc_url=None, openapi_url=None
    )
    install_guard(
        app, verifier, "artifactory-service", registry, keyset, open_prefixes=(IMPORT_PREFIX,)
    )
    pool = ThreadPoolExecutor(max_workers=MAX_RUNNING, thread_name_prefix="import")
    run_later = runner or (lambda fn: pool.submit(fn))
    minimum = _version(min_client_version) or (0,)

    @app.exception_handler(ServiceError)
    async def service_error(_request: Request, exc: ServiceError):
        wired = _wire(exc)
        return JSONResponse(wired.body, status_code=wired.status)

    @app.exception_handler(RetentionError)
    async def retention_error(_request: Request, exc: RetentionError):
        body = {"code": exc.code, "message": exc.message, "retryable": exc.status >= 500}
        return JSONResponse(body, status_code=exc.status)

    # ---------------------------------------------------------------- import calls ---
    def import_owner(request: Request) -> tuple[str, str]:
        client = _version(request.headers.get("x-modelhub-client"))
        if client is None or client < minimum:
            raise _error(
                426,
                "client_too_old",
                f"Update the modelhub program to version {min_client_version} or later.",
                minimumCliVersion=min_client_version,
            )
        scheme, _, value = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not value.strip():
            raise _error(401, "token_invalid", "Sign in with a personal import token.")
        try:
            verdict = catalog.introspect(value.strip())
        except (CatalogUnavailable, AuthUnavailable) as exc:
            raise _error(
                503, "catalog_unavailable", "The Catalog could not be reached.", True
            ) from exc
        if not verdict.get("active"):
            more = (
                " Make a new token in the portal."
                if verdict.get("reason") in ("revoked", "expired")
                else ""
            )
            raise _error(401, "token_invalid", "This token is not accepted." + more)
        return verdict["ownerId"], verdict["ownerName"]

    @app.post(IMPORT_PREFIX)
    async def create_import(request: Request, owner: tuple = Depends(import_owner)):
        try:
            data = await request.json()
        except ValueError:
            data = None
        if not isinstance(data, dict):
            raise _error(422, "bad_request", "The body must be a JSON object.")
        for name in (
            "modelId",
            "commit",
            "bundleName",
            "bundleDescription",
            "bundleSignature",
            "computer",
            "toolVersion",
        ):
            if not isinstance(data.get(name), str) or not data[name]:
                raise _error(422, "bad_request", f"{name} is required.")
        view = await run_in_threadpool(
            importer.create,
            owner[0],
            owner[1],
            data["bundleDescription"].encode("utf-8"),
            data["bundleSignature"].encode("utf-8"),
            data["computer"],
            data["toolVersion"],
            data.get("checkResults") or {},
            data["bundleName"],
            data["modelId"],
            data["commit"],
        )
        return JSONResponse(_shape(view), status_code=200 if view["state"] == "skipped" else 201)

    @app.get(IMPORT_PREFIX + "/{import_id}")
    def get_import(import_id: str, owner: tuple = Depends(import_owner)):
        return _shape(importer.get(import_id, owner[0]))

    @app.delete(IMPORT_PREFIX + "/{import_id}")
    def cancel_import(import_id: str, owner: tuple = Depends(import_owner)):
        try:
            importer.cancel(import_id, owner[0])
        except ServiceError as exc:
            if exc.status not in (404, 409):
                raise
        return Response(status_code=204)

    @app.put(IMPORT_PREFIX + "/{import_id}/pieces/{index}")
    async def put_piece(
        import_id: str, index: int, request: Request, owner: tuple = Depends(import_owner)
    ):
        digest = (request.headers.get("x-piece-sha256") or "").strip().lower()
        if not digest:
            raise _error(422, "bad_request", "X-Piece-SHA256 is required.")
        with tempfile.TemporaryFile() as spool:
            async for chunk in request.stream():
                spool.write(chunk)
            spool.seek(0)
            await run_in_threadpool(importer.put_piece, import_id, owner[0], index, spool, digest)
        return Response(status_code=204)

    @app.post(IMPORT_PREFIX + "/{import_id}/start")
    def start_import(import_id: str, owner: tuple = Depends(import_owner)):
        before = importer.get(import_id, owner[0])
        if before["state"] in ("verifying", "uploading", "recording"):
            return JSONResponse(_shape(before), status_code=202)
        view = importer.start(import_id, owner[0])
        run_later(lambda: importer.run(import_id))
        return JSONResponse(
            _shape(importer.get(import_id, owner[0]) if runner else view), status_code=202
        )

    # ---------------------------------------------------------- retention (C4) ---
    @app.get("/v1/retention/settings")
    def get_settings(person: Verdict = Depends(current_person)):
        return retention.settings()

    @app.put("/v1/retention/settings")
    async def put_settings(request: Request, person: Verdict = Depends(require_admin)):
        data = await request.json()
        return retention.set_period((data or {}).get("periodDays"), person.person_name)

    @app.get("/v1/retention/due")
    def due(person: Verdict = Depends(require_admin)):
        return {"items": retention.due()}

    @app.get("/v1/retention/decisions")
    def decisions(
        model: str | None = None, person: str | None = None, who: Verdict = Depends(current_person)
    ):
        return {"items": retention.decisions(model, person)}

    @app.post("/v1/retention/decisions")
    async def decide(request: Request, person: Verdict = Depends(require_admin)):
        data = await request.json() or {}
        return await run_in_threadpool(
            retention.decide,
            data.get("modelId", ""),
            data.get("commit", ""),
            data.get("decision", ""),
            person.person_id,
            person.person_name,
        )

    # ------------------------------------------------------------ trusted keys ---
    @app.get("/v1/trusted-keys")
    def list_keys(person: Verdict = Depends(require_admin)):
        return {
            "items": [
                {
                    "keyId": k["key_id"],
                    "fingerprint": k["fingerprint"],
                    "name": k["label"],
                    "addedBy": k["added_by_name"],
                    "addedAt": k["added_at"],
                    "status": "revoked" if k["revoked_at"] else "active",
                }
                for k in keys.list()
            ]
        }

    @app.post("/v1/trusted-keys")
    async def add_key(request: Request, person: Verdict = Depends(require_admin)):
        data = await request.json() or {}
        try:
            added = keys.add(
                data.get("publicKey", ""),
                data.get("typedFingerprint", ""),
                data.get("name", ""),
                person.person_id,
                person.person_name,
            )
        except FingerprintMismatch as exc:
            raise _error(422, "fingerprint_mismatch", str(exc)) from exc
        except InvalidKey as exc:
            raise _error(422, "invalid_key", str(exc)) from exc
        except KeyExists as exc:
            raise _error(409, "key_exists", "This key is already trusted.") from exc
        return JSONResponse(
            {"keyId": added["key_id"], "fingerprint": added["fingerprint"], "name": added["label"]},
            status_code=201,
        )

    @app.delete("/v1/trusted-keys/{key_id}")
    def remove_key(key_id: str, person: Verdict = Depends(require_admin)):
        for key in keys.list():
            if key_id in (key["key_id"], key["fingerprint"]):
                keys.revoke(key["fingerprint"], person.person_name)
                break
        return Response(status_code=204)

    app.state.importer = importer
    return app
