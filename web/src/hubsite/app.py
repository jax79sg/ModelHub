"""Routes. URLs mirror huggingface.co so muscle memory (and links in model cards) keep working:

/models                         listing with filters, search, sort, paging
/{org}/{name}                   model card
/{org}/{name}/tree/{rev}[/dir]  files and versions
/{org}/{name}/blob/{rev}/{path} file viewer
/{org}/{name}/resolve/{rev}/..  download
/{org}/{name}/raw/{rev}/{path}  plain text
/{org}/{name}/commits/{rev}     commit history
"""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from urllib.parse import quote, urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi import Query as QueryParam
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import catalog, fmt
from .markdown import render as render_markdown
from .store import HIDDEN_TOP, Model, Store

HERE = Path(__file__).parent
TEXT_LIMIT = 512 * 1024
INLINE_IMAGES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
CSP = "default-src 'none'; img-src 'self' data:; style-src 'self'; script-src 'self'; font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"


def default_store_path() -> Path:
    return Path(os.environ.get("HUBSITE_STORE", "store")).expanduser()


def create_app(store_path: Path | str | None = None) -> FastAPI:
    store = Store(Path(store_path) if store_path else default_store_path())
    app = FastAPI(title="ModelHub", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    env = templates.env
    env.globals.update(
        avatar_class=lambda s: f"av-{sum(map(ord, str(s))) % 12}",
        fmt=fmt,
        catalog=catalog,
        q=lambda s, safe="": quote(str(s), safe=safe),
        qs=lambda pairs: urlencode(pairs),
        HIDDEN_TOP=HIDDEN_TOP,
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    def page(request: Request, name: str, status: int = 200, **ctx) -> HTMLResponse:
        ctx.setdefault("store_empty", not store.models())
        return templates.TemplateResponse(request, name, ctx, status_code=status)

    def not_found(request: Request, message: str) -> HTMLResponse:
        return page(request, "error.html", 404, title="Not found", message=message)

    def model_or_none(org: str, name: str) -> Model | None:
        return store.get(f"{org}/{name}")

    def default_rev(model: Model) -> str:
        return "main" if "main" in model.refs else "latest"

    def revisions(model: Model) -> list[dict]:
        out = [{"name": r, "commit": c, "kind": "branch"} for r, c in sorted(model.refs.items())]
        seen = {r["commit"] for r in out}
        out += [{"name": c[:7], "commit": c, "kind": "commit"} for c in model.commits if c not in seen]
        return out

    def header_ctx(model: Model, rev: str, commit: str, active: str) -> dict:
        s = model.summary_for(commit)
        files = model.entries(commit)
        return dict(
            model=model,
            rev=rev,
            commit=commit,
            summary=s,
            active_tab=active,
            n_commits=len(model.history(commit)),
            revisions=revisions(model),
            is_latest=commit == model.latest,
            files_total=sum(f.size for f in files if f.type == "file"),
            files_in_store=sum(1 for f in files if f.type == "file" and f.in_store),
        )

    def resolve_or_404(model: Model, rev: str) -> str:
        commit = model.resolve(rev)
        if commit is None:
            raise HTTPException(404, f"Revision “{rev}” was not captured for {model.id}.")
        return commit

    # ---------------------------------------------------------------- listing
    @app.get("/")
    def home():
        return RedirectResponse("/models")

    @app.get("/models", response_class=HTMLResponse)
    def models(
        request: Request,
        search: str = "",
        pipeline_tag: list[str] = QueryParam(default=[]),
        library: list[str] = QueryParam(default=[]),
        license: list[str] = QueryParam(default=[]),
        language: list[str] = QueryParam(default=[]),
        other: list[str] = QueryParam(default=[]),
        pmin: int = 0,
        pmax: int = len(fmt.PARAM_LABELS) - 1,
        sort: str = "downloads",
        p: int = 0,
        displayed: str = "main",
        partial: bool = False,
    ):
        query = catalog.Query(search, pipeline_tag, library, license, language, other, pmin, pmax, sort, p, displayed).clamp()
        result = catalog.run(store.models(), query)
        return page(request, "models.html", title="Models", query=query, result=result, partial=partial)

    @app.get("/api/models")
    def api_models(search: str = "", sort: str = "downloads", limit: int = 100, offset: int = 0):
        query = catalog.Query(search=search, sort=sort).clamp()
        hits = catalog.sort_models([m for m in store.models() if catalog.matches(m, query)], query.sort)
        limit = max(1, min(limit, 1000))
        return [
            {
                "id": m.id,
                "latest": m.latest,
                "pipeline_tag": m.pipeline_tag,
                "library_name": m.library,
                "license": m.license,
                "downloads": m.downloads,
                "likes": m.likes,
                "numParameters": m.num_parameters,
                "lastModified": m.last_modified,
                "capturedAt": m.captured_at,
                "tags": m.tags,
            }
            for m in hits[max(0, offset) : max(0, offset) + limit]
        ]

    @app.get("/api/models/{org}/{name}")
    def api_model(org: str, name: str):
        model = model_or_none(org, name)
        if model is None:
            raise HTTPException(404, "Model not in store")
        return JSONResponse({**model.summary, "refs": model.refs, "commits": model.commits})

    # ------------------------------------------------------------- model card
    @app.get("/{org}/{name}", response_class=HTMLResponse)
    def model_card(request: Request, org: str, name: str, rev: str | None = None):
        model = model_or_none(org, name)
        if model is None:
            return not_found(request, f"{org}/{name} is not in this store.")
        rev = rev or default_rev(model)
        commit = resolve_or_404(model, rev)
        readme = model.readme_text(commit)
        rendered = render_markdown(readme[0], model.id, commit, rev) if readme else None
        s = model.summary_for(commit)
        card_tags = (s.get("card") or {}).get("tags") or []
        sidebar = dict(
            datasets=[t.split(":", 1)[1] for t in card_tags if t.startswith("dataset:")],
            papers=[t.split(":", 1)[1] for t in card_tags if t.startswith("arxiv:")],
            dtype_params=((s.get("stats") or {}).get("parameter_counts") or {}).get("parameters") or {},
        )
        return page(
            request,
            "model_card.html",
            title=model.id,
            readme=rendered,
            sidebar=sidebar,
            **header_ctx(model, rev, commit, "card"),
        )

    # ------------------------------------------------------------------ files
    @app.get("/{org}/{name}/tree/{rev}", response_class=HTMLResponse)
    @app.get("/{org}/{name}/tree/{rev}/{path:path}", response_class=HTMLResponse)
    def tree(request: Request, org: str, name: str, rev: str, path: str = ""):
        model = model_or_none(org, name)
        if model is None:
            return not_found(request, f"{org}/{name} is not in this store.")
        commit = resolve_or_404(model, rev)
        path = path.strip("/")
        children = model.listing(commit, path) if not path.startswith(HIDDEN_TOP) else None
        if children is None:
            return not_found(request, f"No folder “{path}” at {rev}.")
        history = model.history(commit)
        crumbs = [(part, "/".join(path.split("/")[: i + 1])) for i, part in enumerate(path.split("/"))] if path else []
        return page(
            request,
            "tree.html",
            title=f"{model.id} at {rev}",
            children=children,
            path=path,
            crumbs=crumbs,
            last_commit=history[0] if history else None,
            contributors=_contributors(history),
            **header_ctx(model, rev, commit, "files"),
        )

    @app.get("/{org}/{name}/blob/{rev}/{path:path}", response_class=HTMLResponse)
    def blob(request: Request, org: str, name: str, rev: str, path: str):
        model = model_or_none(org, name)
        if model is None:
            return not_found(request, f"{org}/{name} is not in this store.")
        commit = resolve_or_404(model, rev)
        entry = model.find_file(commit, path)
        if entry is None or path.startswith(HIDDEN_TOP):
            return not_found(request, f"No file “{path}” at {rev}.")
        view: dict = {"kind": "missing"}
        real = model.file_path(commit, path)
        if real is not None:
            ext = real.suffix.lower()
            if ext in INLINE_IMAGES:
                view = {"kind": "image"}
            else:
                with real.open("rb") as fh:
                    head = fh.read(TEXT_LIMIT + 1)
                if b"\0" in head[:8192]:
                    view = {"kind": "binary"}
                else:
                    text = head[:TEXT_LIMIT].decode("utf-8", errors="replace")
                    view = {"kind": "text", "text": text, "truncated": len(head) > TEXT_LIMIT, "lines": text.count("\n") + 1}
        scan = entry.scan or {}
        pickle = (scan.get("pickleImportScan") or {}).get("pickleImports") or []
        return page(
            request,
            "blob.html",
            title=f"{path} · {model.id}",
            entry=entry,
            path=path,
            view=view,
            pickle_imports=pickle,
            crumbs=[(p, "/".join(path.split("/")[: i + 1])) for i, p in enumerate(path.split("/"))],
            **header_ctx(model, rev, commit, "files"),
        )

    def stored_file(org: str, name: str, rev: str, path: str) -> tuple[Path, Model]:
        model = model_or_none(org, name)
        if model is None:
            raise HTTPException(404, "Model not in store")
        commit = resolve_or_404(model, rev)
        real = None if path.startswith(HIDDEN_TOP) else model.file_path(commit, path)
        if real is None:
            raise HTTPException(404, "File was not included when this model was pulled")
        return real, model

    @app.get("/{org}/{name}/resolve/{rev}/{path:path}")
    def resolve_file(org: str, name: str, rev: str, path: str, inline: bool = False):
        real, _ = stored_file(org, name, rev, path)
        if inline and real.suffix.lower() in INLINE_IMAGES:
            return FileResponse(real, media_type=INLINE_IMAGES[real.suffix.lower()])
        return FileResponse(real, media_type="application/octet-stream", filename=real.name)

    @app.get("/{org}/{name}/raw/{rev}/{path:path}")
    def raw_file(org: str, name: str, rev: str, path: str):
        real, _ = stored_file(org, name, rev, path)
        with real.open("rb") as fh:
            data = fh.read(TEXT_LIMIT * 8)
        if b"\0" in data[:8192]:
            raise HTTPException(415, "Binary file; use /resolve/ to download")
        return PlainTextResponse(data.decode("utf-8", errors="replace"))

    @app.get("/{org}/{name}/readme-asset/{commit}/{path:path}")
    def readme_asset(org: str, name: str, commit: str, path: str):
        model = model_or_none(org, name)
        if model is None or commit not in model.commits:
            raise HTTPException(404, "Not found")
        real = model.asset_path(commit, path)
        if real is None:
            raise HTTPException(404, "Not found")
        media = INLINE_IMAGES.get(real.suffix.lower())
        if media is None:  # svg and anything else could carry script: never serve inline from this origin
            return FileResponse(real, media_type=mimetypes.guess_type(real.name)[0] or "application/octet-stream", filename=real.name)
        return FileResponse(real, media_type=media)

    # ---------------------------------------------------------------- history
    @app.get("/{org}/{name}/commits/{rev}", response_class=HTMLResponse)
    def commits(request: Request, org: str, name: str, rev: str):
        model = model_or_none(org, name)
        if model is None:
            return not_found(request, f"{org}/{name} is not in this store.")
        commit = resolve_or_404(model, rev)
        raw_refs = model.raw_refs(commit)
        tags = {t.get("targetCommit"): t.get("name") for t in raw_refs.get("tags") or [] if isinstance(t, dict)}
        return page(
            request,
            "commits.html",
            title=f"Commits · {model.id}",
            history=model.history(commit),
            tags=tags,
            **header_ctx(model, rev, commit, "files"),
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        if "text/html" in request.headers.get("accept", ""):
            return page(request, "error.html", exc.status_code, title=str(exc.status_code), message=str(exc.detail))
        return PlainTextResponse(str(exc.detail), status_code=exc.status_code)

    return app


def _contributors(history: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for c in history:
        for a in c.get("authors") or []:
            if isinstance(a, dict) and a.get("user"):
                seen.setdefault(a["user"], a)
    return list(seen.values())
