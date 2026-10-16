"""The portal's routes (rules BR1.1 to BR1.6, BR1.8, BR1.10, BR1.11, BR1.12).

Every page needs a session except the sign-in steps, the health paths and the static files. The
pages are server-rendered; the browser holds only a session cookie. The portal serves no model
file: it shows what the Catalog stored (rule BR1.9).
"""

from __future__ import annotations

import hmac
import logging
import posixpath
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit

from fastapi import Depends, FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from hubsite import fmt
from hubsite.markdown import render as render_markdown
from jinja2 import ChoiceLoader, FileSystemLoader
from starlette.middleware.base import BaseHTTPMiddleware

from modelhub_portal.catalog_client import (
    Catalog,
    CatalogDown,
    CatalogRefused,
    Gone,
    TokenRejected,
)
from modelhub_portal.oidc import AuthDown, AuthRefused, Oidc
from modelhub_portal.service_client import RetentionService, ServiceDown, ServiceRefused
from modelhub_portal.sessions import Session, SessionStore

log = logging.getLogger("modelhub.portal")
HERE = Path(__file__).parent
HUBSITE = Path(fmt.__file__).parent
SESSION_COOKIE = "mh_session"
STATE_COOKIE = "mh_state"
PAGE_SIZE = 30
REFRESH_MARGIN = 30
OPEN_EXACT = {"/healthz", "/readyz", "/auth/login", "/auth/callback", "/auth/signed-out"}
CSP = (
    "default-src 'none'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; "
    "frame-ancestors 'none'"
)
PICTURE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
SORTS = [
    ("downloads", "Most downloads"),
    ("likes", "Most likes"),
    ("lastModified", "Recently updated"),
    ("createdAt", "Recently created"),
    ("importedAt", "Recently imported"),
    ("name", "Name (A–Z)"),
]
BANDS = [
    ("lt1b", "< 1B"),
    ("6b", "1B–6B"),
    ("12b", "6B–12B"),
    ("32b", "12B–32B"),
    ("128b", "32B–128B"),
    ("gt500b", "> 500B"),
]
FILTERS = ("task", "library", "license", "language", "parameters", "importedFrom", "importedTo")


@dataclass
class Settings:
    base_url: str
    artifactory_url: str = ""
    hf_repo_key: str = ""
    session_idle_hours: float = 8
    version: str = "0.1.0"

    @property
    def secure(self) -> bool:
        return self.base_url.startswith("https://")

    @property
    def origin(self) -> str:
        parts = urlsplit(self.base_url)
        return f"{parts.scheme}://{parts.netloc}"


def _safe_next(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return "/models"


def create_app(
    settings: Settings,
    oidc: Oidc,
    catalog: Catalog,
    clock: Callable[[], float] = time.time,
    service: RetentionService | None = None,
) -> FastAPI:
    sessions = SessionStore(settings.session_idle_hours * 3600, clock)
    pending: dict[str, tuple[str, str, float]] = {}
    app = FastAPI(title="ModelHub", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.sessions = sessions
    app.state.catalog_http = getattr(catalog, "_http", None)
    app.mount("/static", StaticFiles(directory=HUBSITE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.loader = ChoiceLoader(
        [FileSystemLoader(HERE / "templates"), FileSystemLoader(HUBSITE / "templates")]
    )
    templates.env.globals.update(
        fmt=fmt,
        q=lambda s, safe="": quote(str(s), safe=safe),
        qs=lambda pairs: urlencode(pairs),
        unknown=lambda v: "unknown" if v is None else v,
        version=settings.version,
    )

    # ------------------------------------------------------------------ helpers ---
    def page(request: Request, template: str, status: int = 200, **ctx) -> HTMLResponse:
        ctx.setdefault("session", getattr(request.state, "session", None))
        return templates.TemplateResponse(request, template, ctx, status_code=status)

    def error_page(
        request: Request, status: int, title: str, message: str, retry=None, signin=False
    ):
        return page(
            request,
            "error.html",
            status,
            title=title,
            message=message,
            retry=retry,
            signin=signin,
            request_id=getattr(request.state, "request_id", ""),
        )

    def rid(request: Request) -> str:
        return getattr(request.state, "request_id", "")

    def token_of(request: Request) -> str:
        return request.state.session.access_token

    def set_cookie(response: Response, name: str, value: str, max_age=None, path="/") -> None:
        response.set_cookie(
            name,
            value,
            max_age=max_age,
            path=path,
            httponly=True,
            secure=settings.secure,
            samesite="lax",
        )

    # --------------------------------------------------------------- the gate ---
    async def refresh_if_needed(session: Session) -> bool:
        """False when the session is gone; leaves it usable while Keycloak is down (BR1.11)."""
        if session.access_expires - clock() > REFRESH_MARGIN or not session.refresh_token:
            return True
        try:
            tokens = await run_in_threadpool(oidc.refresh, session.refresh_token)
            verdict = await run_in_threadpool(oidc.identity, tokens["access_token"])
        except AuthRefused:
            sessions.delete(session.id)
            return False
        except AuthDown:
            session.token_expired = session.access_expires <= clock()
            return True
        session.access_token = tokens["access_token"]
        session.refresh_token = tokens.get("refresh_token", session.refresh_token)
        session.access_expires = clock() + float(tokens.get("expires_in", 300))
        session.is_admin = verdict.is_admin
        session.token_expired = False
        return True

    class Gate(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
            request.state.session = None
            path = request.url.path
            is_open = path in OPEN_EXACT or path.startswith("/static/")
            response = None
            session = sessions.get(request.cookies.get(SESSION_COOKIE))
            if session is not None and not is_open and not await refresh_if_needed(session):
                session = None
            if session is not None:
                request.state.session = session
            if not is_open and session is None:
                nxt = path + (f"?{request.url.query}" if request.url.query else "")
                response = RedirectResponse("/auth/login?" + urlencode({"next": nxt}), 302)
            elif session is not None and session.token_expired and not is_open:
                response = error_page(
                    request,
                    401,
                    "Sign in again",
                    "Your sign-in has expired and the sign-in service cannot be reached. "
                    "Please sign in again when it is back.",
                    signin=True,
                )
            if response is None:
                try:
                    response = await call_next(request)
                except Exception:
                    log.exception("unhandled error", extra={"requestId": request.state.request_id})
                    response = error_page(
                        request, 500, "Something went wrong", "The page could not be shown."
                    )
            response.headers.setdefault("Content-Security-Policy", CSP)
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            if not path.startswith("/static/"):
                response.headers.setdefault("Cache-Control", "no-store")
            response.headers["X-Request-Id"] = request.state.request_id
            return response

    app.add_middleware(Gate)

    async def checked_form(request: Request):
        """The submitted form, after the origin and the form token are checked (BR1.3)."""
        origin = request.headers.get("origin")
        if not origin:
            ref = request.headers.get("referer", "")
            origin = f"{urlsplit(ref).scheme}://{urlsplit(ref).netloc}" if ref else ""
        form = await request.form()
        session = request.state.session
        sent = str(form.get("_csrf", ""))
        if origin != settings.origin or not session or not hmac.compare_digest(sent, session.csrf):
            raise _Forbidden()
        return form

    class _Forbidden(Exception):
        pass

    @app.exception_handler(_Forbidden)
    async def forbidden(request: Request, exc: _Forbidden):
        return error_page(
            request, 403, "Not allowed", "This request was refused and nothing was changed."
        )

    @app.exception_handler(CatalogDown)
    async def catalog_down(request: Request, exc: CatalogDown):
        return error_page(
            request,
            503,
            "Cannot reach the model database",
            "The model database cannot be reached. Nothing is shown until it is back.",
            retry=request.url.path + (f"?{request.url.query}" if request.url.query else ""),
        )

    class _NotAdmin(Exception):
        pass

    @app.exception_handler(_NotAdmin)
    async def not_admin(request: Request, exc: _NotAdmin):
        return error_page(
            request,
            403,
            "Administrator needed",
            "This needs an administrator. Nothing was changed.",
        )

    @app.exception_handler(ServiceDown)
    async def service_down(request: Request, exc: ServiceDown):
        return error_page(
            request,
            503,
            "Cannot reach the retention service",
            "The retention service cannot be reached. Nothing was changed.",
            retry=request.url.path + (f"?{request.url.query}" if request.url.query else ""),
        )

    @app.exception_handler(TokenRejected)
    async def token_rejected(request: Request, exc: TokenRejected):
        return error_page(
            request, 401, "Sign in again", "Your sign-in is no longer accepted.", signin=True
        )

    # ------------------------------------------------------------------ health ---
    @app.get("/healthz", include_in_schema=False)
    def healthz():
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    def readyz():
        keycloak = "ok"
        try:
            oidc.metadata()
        except AuthDown:
            keycloak = "degraded"
        return JSONResponse(
            {"status": "ok" if keycloak == "ok" else "degraded", "keycloak": keycloak}
        )

    # ----------------------------------------------------------------- sign-in ---
    @app.get("/auth/login")
    async def login(request: Request, next: str = "/models"):
        try:
            url, state, verifier = await run_in_threadpool(oidc.start)
        except AuthDown:
            return error_page(
                request,
                503,
                "Sign-in unavailable",
                "The sign-in service cannot be reached just now. Please try again in a few minutes.",
                retry="/auth/login",
            )
        now = clock()
        for old in [s for s, (_, _, until) in pending.items() if until < now]:
            del pending[old]
        pending[state] = (verifier, _safe_next(next), now + 600)
        response = RedirectResponse(url, 302)
        set_cookie(response, STATE_COOKIE, state, max_age=600, path="/auth")
        return response

    @app.get("/auth/callback")
    async def callback(request: Request, code: str = "", state: str = "", error: str = ""):
        cookie = request.cookies.get(STATE_COOKIE, "")
        entry = pending.pop(state, None)
        if error or not code or entry is None or not hmac.compare_digest(cookie, state):
            return error_page(
                request,
                400,
                "Sign-in not completed",
                "The sign-in could not be completed. Please start again.",
                retry="/auth/login",
            )
        verifier, nxt, _ = entry
        try:
            tokens = await run_in_threadpool(oidc.exchange, code, verifier)
            verdict = await run_in_threadpool(oidc.identity, tokens["access_token"])
        except AuthDown:
            return error_page(
                request,
                503,
                "Sign-in unavailable",
                "The sign-in service cannot be reached.",
                retry="/auth/login",
            )
        except AuthRefused:
            return error_page(
                request,
                400,
                "Sign-in not completed",
                "The sign-in was not accepted.",
                retry="/auth/login",
            )
        session = sessions.create(
            tokens["access_token"],
            tokens.get("refresh_token"),
            clock() + float(tokens.get("expires_in", 300)),
            verdict.person_id,
            verdict.person_name,
            verdict.is_admin,
        )
        response = RedirectResponse(nxt, 302)
        set_cookie(response, SESSION_COOKIE, session.id)
        response.delete_cookie(STATE_COOKIE, path="/auth")
        return response

    @app.post("/auth/logout")
    async def logout(request: Request, form=Depends(checked_form)):
        session = request.state.session
        refresh = session.refresh_token
        sessions.delete(session.id)
        await run_in_threadpool(oidc.logout, refresh)
        response = RedirectResponse("/auth/signed-out", 302)
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response

    @app.get("/auth/signed-out", response_class=HTMLResponse)
    def signed_out(request: Request):
        return page(request, "signed_out.html", title="Signed out")

    # -------------------------------------------------------------- models list ---
    @app.get("/")
    def home():
        return RedirectResponse("/models")

    def list_args(request: Request) -> tuple[dict, dict]:
        """(what to ask the Catalog, what to keep in links)."""
        qp = request.query_params
        keep = {k: qp[k] for k in (*FILTERS, "sort", "search", "showRemoved") if qp.get(k)}
        ask = {k: v for k, v in keep.items() if k not in ("search", "showRemoved")}
        if keep.get("search"):
            ask["q"] = keep["search"]
        if keep.get("showRemoved"):
            ask["showRemoved"] = "true"
        try:
            number = max(1, int(qp.get("p", "1")))
        except ValueError:
            number = 1
        ask.update(page=number, pageSize=PAGE_SIZE)
        return ask, keep

    @app.get("/models", response_class=HTMLResponse)
    def models(request: Request):
        ask, keep = list_args(request)
        notice = None
        try:
            result = catalog.models(token_of(request), ask, rid(request))
        except CatalogRefused as exc:
            if exc.status != 422:
                raise
            notice = exc.message or "That choice is not valid, so the unfiltered list is shown."
            ask, keep = {"page": 1, "pageSize": PAGE_SIZE}, {}
            result = catalog.models(token_of(request), ask, rid(request))
        pages = max(1, -(-result["total"] // PAGE_SIZE))

        def link(**change) -> str:
            merged = {**keep, **change}
            return "/models?" + urlencode({k: v for k, v in merged.items() if v not in (None, "")})

        return page(
            request,
            "models.html",
            title="Models",
            result=result,
            keep=keep,
            notice=notice,
            pages=pages,
            current=result["page"],
            link=link,
            sorts=SORTS,
            bands=BANDS,
        )

    # --------------------------------------------------------------- tokens page ---
    @app.get("/account/tokens", response_class=HTMLResponse)
    def tokens_page(request: Request, all: str = ""):
        session = request.state.session
        everyone = bool(all) and session.is_admin
        items = catalog.list_tokens(token_of(request), everyone, rid(request))
        return page(
            request,
            "tokens.html",
            title="Personal tokens",
            items=items,
            everyone=everyone,
            message=None,
        )

    @app.post("/account/tokens", response_class=HTMLResponse)
    async def make_token(request: Request, form=Depends(checked_form)):
        name = str(form.get("name", "")).strip()
        try:
            made = await run_in_threadpool(
                catalog.make_token, token_of(request), name, rid(request)
            )
        except CatalogRefused as exc:
            items = catalog.list_tokens(token_of(request), False, rid(request))
            return page(
                request,
                "tokens.html",
                422,
                title="Personal tokens",
                items=items,
                everyone=False,
                message=exc.message or "The token could not be made.",
            )
        # The value is shown here once: no-store, never in an address, never logged (BR1.12).
        return page(request, "token_made.html", title="Your new token", made=made, name=name)

    @app.get("/account/tokens/{token_id}/revoke", response_class=HTMLResponse)
    def confirm_revoke(request: Request, token_id: str):
        return page(request, "confirm_revoke.html", title="Revoke token", token_id=token_id)

    @app.post("/account/tokens/{token_id}/revoke")
    async def revoke(request: Request, token_id: str, form=Depends(checked_form)):
        await run_in_threadpool(catalog.revoke_token, token_of(request), token_id, rid(request))
        return RedirectResponse("/account/tokens", 303)

    # ------------------------------------------------------- retention and keys ---
    def svc() -> RetentionService:
        if service is None:
            raise ServiceDown("not configured")
        return service

    def admin_only(request: Request) -> None:
        if not request.state.session.is_admin:
            raise _NotAdmin()

    async def admin_form(request: Request):
        admin_only(request)
        return await checked_form(request)

    def retention_page(request: Request, status: int = 200, message: str | None = None):
        session = request.state.session
        token = token_of(request)
        settings_ = svc().settings(token, rid(request))
        due = decisions = None
        if session.is_admin:
            due = svc().due(token, rid(request))
            decisions = svc().decisions(token, rid(request))
        return page(
            request,
            "retention.html",
            status,
            title="Retention",
            period=settings_,
            due=due,
            decisions=decisions,
            message=message,
        )

    @app.get("/admin/retention", response_class=HTMLResponse)
    def retention(request: Request):
        return retention_page(request)

    @app.post("/admin/retention/period", response_class=HTMLResponse)
    async def set_period(request: Request, form=Depends(admin_form)):
        try:
            days = int(str(form.get("days", "")).strip())
        except ValueError:
            return await run_in_threadpool(
                retention_page, request, 422, "The period is a whole number of days, 1 to 3650."
            )
        try:
            await run_in_threadpool(svc().set_period, token_of(request), days, rid(request))
        except ServiceRefused as exc:
            return await run_in_threadpool(retention_page, request, 422, exc.message)
        return RedirectResponse("/admin/retention", 303)

    def decide_result(request: Request, model: str, commit: str, decision: str):
        try:
            return svc().decide(token_of(request), model, commit, decision, rid(request)), None
        except ServiceRefused as exc:
            return None, exc

    @app.post("/admin/retention/keep", response_class=HTMLResponse)
    async def keep(request: Request, form=Depends(admin_form)):
        model, commit = str(form.get("model", "")), str(form.get("commit", ""))
        _, refused = await run_in_threadpool(decide_result, request, model, commit, "keep")
        if refused:
            status = 409 if refused.status == 409 else 422
            return page(
                request,
                "retention_result.html",
                status,
                title="Retention",
                model=model,
                commit=commit,
                outcome="refused",
                message=_decided_text(refused),
            )
        return RedirectResponse("/admin/retention", 303)

    def _decided_text(refused: ServiceRefused) -> str:
        if refused.status == 409:
            return "This version was already decided, or is not an imported version."
        return refused.message or "The decision was refused."

    @app.get("/admin/retention/remove", response_class=HTMLResponse)
    def confirm_remove(request: Request, model: str = "", commit: str = ""):
        admin_only(request)
        return page(
            request, "retention_confirm.html", title="Remove version", model=model, commit=commit
        )

    @app.post("/admin/retention/remove", response_class=HTMLResponse)
    async def remove(request: Request, form=Depends(admin_form)):
        model, commit = str(form.get("model", "")), str(form.get("commit", ""))
        result, refused = await run_in_threadpool(decide_result, request, model, commit, "remove")
        if refused:
            status = 409 if refused.status == 409 else 422
            return page(
                request,
                "retention_result.html",
                status,
                title="Retention",
                model=model,
                commit=commit,
                outcome="refused",
                message=_decided_text(refused),
            )
        return page(
            request,
            "retention_result.html",
            title="Retention",
            model=model,
            commit=commit,
            outcome=result.get("outcome"),
            message=result.get("message"),
        )

    def keys_page(request: Request, status: int = 200, message: str | None = None):
        items = svc().keys(token_of(request), rid(request))
        return page(
            request, "keys.html", status, title="Trusted keys", items=items, message=message
        )

    @app.get("/admin/keys", response_class=HTMLResponse)
    def keys(request: Request):
        admin_only(request)
        return keys_page(request)

    @app.post("/admin/keys", response_class=HTMLResponse)
    async def add_key(request: Request, form=Depends(admin_form)):
        try:
            await run_in_threadpool(
                svc().add_key,
                token_of(request),
                str(form.get("public_key", "")),
                str(form.get("fingerprint", "")),
                str(form.get("name", "")),
                rid(request),
            )
        except ServiceRefused as exc:
            text = {
                "fingerprint_mismatch": "The fingerprint you typed does not match this key. Nothing was added.",
                "key_exists": "This key is already trusted.",
            }.get(exc.code, exc.message or "The key was not added.")
            return await run_in_threadpool(keys_page, request, 422, text)
        return RedirectResponse("/admin/keys", 303)

    @app.get("/admin/keys/{key_id}/remove", response_class=HTMLResponse)
    def confirm_key_remove(request: Request, key_id: str):
        admin_only(request)
        return page(request, "keys_confirm.html", title="Stop trusting a key", key_id=key_id)

    @app.post("/admin/keys/{key_id}/remove")
    async def remove_key(request: Request, key_id: str, form=Depends(admin_form)):
        await run_in_threadpool(svc().remove_key, token_of(request), key_id, rid(request))
        return RedirectResponse("/admin/keys", 303)

    # --------------------------------------------------------------- model pages ---
    def pick_commit(model: dict, rev: str | None) -> tuple[str | None, str | None]:
        """(commit, problem)."""
        versions = model["versions"]
        if not rev:
            imported = [v for v in versions if v["state"] == "imported"]
            return ((imported or versions)[0]["commit"], None)
        for ref in model["refs"]:
            if ref["name"] == rev:
                return ref["commit"], None
        matches = [
            v["commit"] for v in versions if len(rev) >= 7 and v["commit"].startswith(rev.lower())
        ]
        if len(matches) == 1:
            return matches[0], None
        if len(matches) > 1:
            return None, "That short commit matches more than one version; type more characters."
        return None, f"The revision “{rev}” was not captured for this model."

    def text_document(request: Request, model_id: str, commit: str, docs: list[dict]):
        for kind, name in (("readme_local", "README.local.md"), ("readme", "README.md")):
            if any(d["kind"] == kind and d["name"] == name for d in docs):
                try:
                    found = catalog.document(
                        token_of(request), model_id, commit, kind, name, rid(request)
                    )
                except Gone:
                    return None
                if found:
                    return found[0].decode("utf-8", errors="replace")
        return None

    def fetch_snippets(model_id: str, commit: str) -> dict:
        base = settings.artifactory_url.rstrip("/")
        endpoint = f"{base}/artifactory/api/huggingfaceml/{settings.hf_repo_key}"
        return {
            "repository": f"{base}/artifactory/{settings.hf_repo_key}",
            "endpoint": endpoint,
            "jf": f"jf hf download {model_id} --revision {commit} --repo-key {settings.hf_repo_key}",
            "python": (
                "import os\n"
                f'os.environ["HF_ENDPOINT"] = "{endpoint}"\n'
                'os.environ["HF_TOKEN"] = "<your-token>"\n'
                "from huggingface_hub import snapshot_download\n"
                f'snapshot_download("{model_id}", revision="{commit}")'
            ),
            "env": f'export HF_ENDPOINT="{endpoint}"\nexport HF_TOKEN="<your-token>"',
        }

    @app.get("/{org}/{name}/readme-asset/{commit}/{path:path}")
    def readme_asset(request: Request, org: str, name: str, commit: str, path: str):
        picture = posixpath.basename(path)
        try:
            found = catalog.document(
                token_of(request), f"{org}/{name}", commit, "picture", picture, rid(request)
            )
        except Gone:
            found = None
        if not found or not found[0]:
            return Response("No picture stored.", status_code=404, media_type="text/plain")
        data, _ = found
        media = PICTURE_TYPES.get(posixpath.splitext(picture)[1].lower())
        headers = {
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Cache-Control": "private, max-age=300",
        }
        if media is None:  # anything else, svg included, could carry script: never render it here
            headers["Content-Disposition"] = 'attachment; filename="picture"'
            return Response(data, media_type="application/octet-stream", headers=headers)
        return Response(data, media_type=media, headers=headers)

    @app.get("/{org}/{name}", response_class=HTMLResponse)
    def model_page(request: Request, org: str, name: str, rev: str | None = None):
        model_id = f"{org}/{name}"
        token = token_of(request)
        model = catalog.model(token, model_id, rid(request))
        if model is None:
            return error_page(request, 404, "Not found", f"{model_id} has not been imported.")
        commit, problem = pick_commit(model, rev)
        if commit is None:
            return error_page(
                request, 404 if "captured" in (problem or "") else 400, "Revision", problem or ""
            )
        version = catalog.version(token, model_id, commit, rid(request))
        if version is None:
            return error_page(request, 404, "Not found", f"{model_id} has no version {commit[:7]}.")
        label = rev or commit
        text = text_document(request, model_id, commit, version.get("documents", []))
        readme = render_markdown(text, model_id, commit, label) if text is not None else None
        revisions = [
            {"name": r["name"], "kind": r["kind"], "commit": r["commit"]} for r in model["refs"]
        ]
        known = {r["commit"] for r in revisions}
        revisions += [
            {"name": v["commit"][:7], "kind": "commit", "commit": v["commit"]}
            for v in model["versions"]
            if v["commit"] not in known
        ]
        return page(
            request,
            "model.html",
            title=model_id,
            model=model,
            version=version,
            commit=commit,
            readme=readme,
            revisions=revisions,
            snippets=fetch_snippets(model_id, commit),
            rev=label,
        )

    return app
