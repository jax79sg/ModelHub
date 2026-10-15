"""The request guard (rules BR1.2, BR1.3, BR1.5, BR1.9; contract C6, C7).

Every path needs a valid token except /healthz, /readyz and paths a service names one by one
(no patterns). A refused token gets the same minimal 401; the reason is logged as a fixed code.
Each request gets a request id (kept from the caller when valid) and one access log line.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable, Iterable

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .health import HealthRegistry
from .keys import KeySet
from .logs import valid_request_id
from .tokens import TokenVerifier, Verdict

HEALTH_PATHS = ("/healthz", "/readyz")
log = logging.getLogger("modelhub.guard")
access_log = logging.getLogger("modelhub.access")

TOKEN_INVALID = {"code": "token_invalid", "message": "Sign-in is required."}
FORBIDDEN = {"code": "forbidden", "message": "You are not allowed to do that."}
INTERNAL = {"code": "internal_error", "message": "Something went wrong."}


class ApiError(Exception):
    """An error answered as the contract's plain {code, message} body."""

    def __init__(self, status: int, body: dict) -> None:
        super().__init__(body["code"])
        self.status = status
        self.body = body


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


class GuardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, verifier: TokenVerifier, open_paths: Iterable[str]) -> None:
        super().__init__(app)
        self._verifier = verifier
        self._open = frozenset(HEALTH_PATHS) | frozenset(open_paths)

    async def dispatch(self, request: Request, call_next: Callable):
        started = time.monotonic()
        rid = request.headers.get("x-request-id")
        if not valid_request_id(rid):
            rid = uuid.uuid4().hex
        request.state.request_id = rid
        request.state.person = None
        response = None
        if request.url.path not in self._open:
            verdict = self._verifier.verify(_bearer(request))
            if not verdict.valid:
                log.warning(
                    "token rejected",
                    extra={
                        "event": "token_rejected",
                        "reason": verdict.reason.value,
                        "requestId": rid,
                    },
                )
                response = JSONResponse(TOKEN_INVALID, status_code=401)
            else:
                request.state.person = verdict
        if response is None:
            try:
                response = await call_next(request)
            except Exception:
                log.exception(
                    "unhandled error", extra={"event": "unhandled_error", "requestId": rid}
                )
                response = JSONResponse(INTERNAL, status_code=500)
        response.headers["X-Request-Id"] = rid
        person = request.state.person
        access_log.info(
            "request",
            extra={
                "event": "access",
                "requestId": rid,
                "person": person.person_name if person else None,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000, 1),
            },
        )
        return response


def install_guard(
    app: FastAPI,
    verifier: TokenVerifier,
    service: str,
    registry: HealthRegistry,
    keys: KeySet,
    open_paths: Iterable[str] = (),
) -> None:
    """Add the guard, /healthz and /readyz to a service's app."""

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    def readyz():
        status, body = registry.ready(keys.state)
        return JSONResponse(body, status_code=status)

    @app.exception_handler(ApiError)
    async def api_error(_request: Request, exc: ApiError):
        return JSONResponse(exc.body, status_code=exc.status)

    app.add_middleware(GuardMiddleware, verifier=verifier, open_paths=tuple(open_paths))
    app.state.service = service


def current_person(request: Request) -> Verdict:
    person = getattr(request.state, "person", None)
    if person is None:
        raise ApiError(401, TOKEN_INVALID)
    return person


def _forbid(request: Request, person: Verdict, why: str) -> ApiError:
    log.warning(
        "forbidden",
        extra={
            "event": "forbidden",
            "person": person.person_name,
            "why": why,
            "requestId": getattr(request.state, "request_id", None),
        },
    )
    return ApiError(403, FORBIDDEN)


def require_admin(request: Request, person: Verdict = Depends(current_person)) -> Verdict:
    if not person.is_admin:
        raise _forbid(request, person, "administrator role required")
    return person


def require_client(client_id: str):
    """A dependency that accepts only tokens of one service client (client credentials)."""

    def dependency(request: Request, person: Verdict = Depends(current_person)) -> Verdict:
        if person.client_id != client_id:
            raise _forbid(request, person, "service identity required")
        return person

    return dependency
