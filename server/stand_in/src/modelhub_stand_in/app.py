"""The HTTP surface of the stand-in: only the calls our system makes (rule BR1.16).

Routes follow what ``huggingface_hub`` (``upload_folder``, ``snapshot_download``) calls under
Artifactory's Hugging Face endpoint, plus the storage-style listing and delete the gateway needs.
Behaviours JFrog does not document are listed in ``assumptions.json``.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .rules import is_commit_hash, safe_relative_path, validate_names
from .store import Store, StoredFile, Version, sha256_hex
from .switches import Switch, SwitchTable

HF = "/artifactory/api/huggingfaceml/{repo_key}"
BLOCK = 64 * 1024


def error(status: int, code: str, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"code": code, "message": message}, status_code=status, headers=headers)


def upload_key(state, oid: str) -> str:
    """The key in a large-file upload address: the client does not send our token there."""
    return hmac.new(state.token.encode(), oid.lower().encode(), hashlib.sha256).hexdigest()[:32]


def _upload_key_ok(state, request) -> bool:
    oid = request.url.path.rsplit("/", 1)[-1]
    given = request.query_params.get("key", "")
    return hmac.compare_digest(given, upload_key(state, oid))


def classify(method: str, path: str) -> str:
    """The call group of a request, used for failure-switch scopes and write permission."""
    if "/artifactory/api/storage/" in path:
        return "listing"
    if path.endswith("/api/repos/create"):
        return "create"
    if path.endswith("/api/validate-yaml"):
        return "preupload"
    if "/preupload/" in path:
        return "preupload"
    if path.endswith("/info/lfs/objects/batch"):
        return "large-file-batch"
    if "/lfs-upload/" in path:
        return "large-file-upload"
    if "/commit/" in path and method == "POST":
        return "commit"
    if method == "DELETE":
        return "delete"
    if "/resolve/" in path:
        return "fetch"
    if "/tree/" in path or "/revision/" in path or "/paths-info/" in path or "/api/models/" in path:
        return "listing"
    return "other"


CHANGING = {"create", "preupload", "large-file-batch", "large-file-upload", "commit", "delete"}


class State:
    """Everything one running stand-in shares between requests."""

    def __init__(self, token: str, repo_key: str, store: Store) -> None:
        self.token = token
        self.repo_key = repo_key
        self.store = store
        self.switches = SwitchTable()
        self.calls: list[dict] = []
        self._seq = 0
        self.base_url = ""

    def record(self, method: str, path: str, status: int, switch: Switch | None) -> None:
        with self.store.lock:
            self._seq += 1
            self.calls.append(
                {
                    "sequence": self._seq,
                    "method": method,
                    "path": path,
                    "status": status,
                    "received_at": datetime.now(timezone.utc).isoformat(),
                    "switch_fired": switch.kind if switch else None,
                }
            )


def create_app(state: State) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    store = state.store

    @app.middleware("http")
    async def rules_in_order(request: Request, call_next):
        path = request.url.path
        group = classify(request.method, path)
        request.state.switch = None
        if path.startswith("/__control/"):
            return await call_next(request)
        switch = state.switches.check(group)
        request.state.switch = switch
        response = None
        if switch is not None:
            response = await _apply_switch(switch)
        if response is None:
            header = request.headers.get("authorization", "")
            signed = group == "large-file-upload" and _upload_key_ok(state, request)
            if header != f"Bearer {state.token}" and not signed:
                response = error(401, "unauthorised", "A valid token is required.")
            elif group in CHANGING and not store.write_allowed:
                response = error(403, "forbidden", "This token may not change anything.")
        if response is None:
            try:
                response = await call_next(request)
            except Exception:
                state.record(request.method, path, 500, switch)
                raise
        state.record(request.method, path, response.status_code, switch)
        return response

    async def _apply_switch(switch: Switch):
        if switch.kind == "unauthorised":
            return error(401, "unauthorised", "A valid token is required.")
        if switch.kind == "forbidden":
            return error(403, "forbidden", "Not allowed.")
        if switch.kind == "conflict":
            return error(409, "conflict", "Version already exists.")
        if switch.kind == "name-refused":
            return error(400, "name_refused", "The name breaks a naming rule.")
        if switch.kind == "server-error":
            return error(500, "server_error", "Imitated server error.")
        if switch.kind == "slow":
            await asyncio.sleep(switch.seconds)
        return None  # slow, cut-transfer and half-version act inside the handlers

    # --- helpers -----------------------------------------------------------------------------
    def check_repo(repo_key: str) -> JSONResponse | None:
        if repo_key != state.repo_key:
            return error(
                404, "repo_not_found", "No such repository.", {"X-Error-Code": "RepoNotFound"}
            )
        return None

    def not_found(kind: str = "RepoNotFound") -> JSONResponse:
        return error(404, "not_found", "Not found.", {"X-Error-Code": kind})

    # --- create ------------------------------------------------------------------------------
    @app.post(HF + "/api/repos/create")
    async def create_repo(repo_key: str, request: Request):
        if (bad := check_repo(repo_key)) is not None:
            return bad
        body = await request.json()
        org, name = body.get("organization") or "", body.get("name") or ""
        if "/" in name and not org:
            org, name = name.split("/", 1)
        problem = validate_names(org, name, "main")
        if problem and not problem.startswith("revision"):
            return error(400, "name_rule_broken", problem)
        with store.lock:
            if (org, name) in store.repos:
                return error(409, "exists", "Repository already exists.")
            store.repos.add((org, name))
        return {"url": f"{state.base_url}/{org}/{name}", "name": name, "id": f"{org}/{name}"}

    # --- upload: the client checks a README's card metadata before committing it -----------------
    @app.post(HF + "/api/validate-yaml")
    async def validate_yaml(repo_key: str):
        if (bad := check_repo(repo_key)) is not None:
            return bad
        return {"errors": [], "warnings": []}

    # --- upload: pre-upload check ------------------------------------------------------------
    @app.post(HF + "/api/models/{org}/{model}/preupload/{revision}")
    async def preupload(repo_key: str, org: str, model: str, revision: str, request: Request):
        if (bad := check_repo(repo_key)) is not None:
            return bad
        if (problem := validate_names(org, model, revision)) is not None:
            return error(400, "name_rule_broken", problem)
        body = await request.json()
        files = []
        for entry in body.get("files", []):
            path = entry.get("path", "")
            if not safe_relative_path(path):
                return error(400, "unsafe_path", "A file path leaves the version's folder.")
            files.append(
                {
                    "path": path,
                    "uploadMode": store.upload_mode(path, int(entry.get("size", 0))),
                    "shouldIgnore": False,
                    "oid": None,
                }
            )
        with store.lock:
            real = store.resolve(org, model, revision)
            store.versions.setdefault((org, model, real), Version(org, model, real))
        return {"files": files, "commitOid": None}

    # --- upload: large-file batch and object upload ------------------------------------------
    @app.post(HF + "/{org}/{model}.git/info/lfs/objects/batch")
    async def lfs_batch(repo_key: str, org: str, model: str, request: Request):
        if (bad := check_repo(repo_key)) is not None:
            return bad
        body = await request.json()
        objects = []
        for obj in body.get("objects", []):
            oid, size = obj["oid"], int(obj["size"])
            base = f"{state.base_url}{HF.format(repo_key=repo_key)}"
            href = f"{base}/lfs-upload/{org}/{model}/{oid}?key={upload_key(state, oid)}"
            objects.append(
                {
                    "oid": oid,
                    "size": size,
                    "authenticated": True,
                    "actions": {"upload": {"href": href, "header": {}}},
                }
            )
        return JSONResponse(
            {"transfer": "basic", "objects": objects}, media_type="application/vnd.git-lfs+json"
        )

    @app.put(HF + "/lfs-upload/{org}/{model}/{oid}")
    async def lfs_upload(repo_key: str, org: str, model: str, oid: str, request: Request):
        if (bad := check_repo(repo_key)) is not None:
            return bad
        declared = request.headers.get("content-length")
        size_hint = int(declared) if declared else None
        keep = size_hint is not None and (size_hint <= store.keep_limit or bool(store.keep_paths))
        digest = hashlib.sha256()
        total = 0
        tmp = store.workdir / f"upload-{uuid.uuid4().hex}"
        switch: Switch | None = request.state.switch
        cut_at = (size_hint or 0) // 2 if switch and switch.kind == "cut-transfer" else None
        with tmp.open("wb") if keep else _null() as out:
            async for chunk in request.stream():
                digest.update(chunk)
                total += len(chunk)
                if out is not None:
                    out.write(chunk)
                if cut_at is not None and total >= cut_at:
                    tmp.unlink(missing_ok=True)
                    raise RuntimeError("imitated: the transfer was cut")
        if digest.hexdigest() != oid.lower():
            tmp.unlink(missing_ok=True)
            return error(422, "checksum_mismatch", "The content does not match its checksum.")
        stored = None
        if keep:
            stored = store.content / oid.lower()
            tmp.replace(stored)
        with store.lock:
            store.objects[oid.lower()] = (total, stored)
        return Response(status_code=200)

    # --- upload: commit ----------------------------------------------------------------------
    @app.post(HF + "/api/models/{org}/{model}/commit/{revision}")
    async def commit(repo_key: str, org: str, model: str, revision: str, request: Request):
        if (bad := check_repo(repo_key)) is not None:
            return bad
        if (problem := validate_names(org, model, revision)) is not None:
            return error(400, "name_rule_broken", problem)
        raw = (await request.body()).decode("utf-8")
        files: list[StoredFile] = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            key, value = item.get("key"), item.get("value", {})
            if key == "file":
                path = value.get("path", "")
                if not safe_relative_path(path):
                    return error(400, "unsafe_path", "A file path leaves the version's folder.")
                data = base64.b64decode(value.get("content", ""))
                sha = sha256_hex(data)
                if store.keeps(len(data), path):
                    files.append(
                        StoredFile(path, len(data), sha, "kept", "regular", store.keep_bytes(data))
                    )
                else:
                    files.append(StoredFile(path, len(data), sha, "virtual", "regular"))
            elif key == "lfsFile":
                path = value.get("path", "")
                if not safe_relative_path(path):
                    return error(400, "unsafe_path", "A file path leaves the version's folder.")
                oid = value["oid"].lower()
                with store.lock:
                    size, stored = store.objects.get(oid, (int(value.get("size", 0)), None))
                keep = stored is not None and store.keeps(size, path)
                files.append(
                    StoredFile(
                        path,
                        size,
                        oid,
                        "kept" if keep else "virtual",
                        "large-file",
                        stored if keep else None,
                    )
                )
        with store.lock:
            existing = store.get(org, model, revision)
            if existing is not None and not store.overwrite_allowed:
                return error(409, "conflict", "This version already exists.")
            real = store.final_revision(revision, files)
            version = store.versions.get((org, model, real)) or Version(org, model, real)
            store.versions[(org, model, real)] = version
            switch: Switch | None = request.state.switch
            if switch is not None and switch.kind == "half-version":
                version.files = {f.path: f for f in files[: max(1, len(files) // 2)]}
                version.state = "partial"
                return error(500, "server_error", "Imitated failure part-way through the commit.")
            version.files = {f.path: f for f in files}
            version.state = "complete"
            version.committed_at = store.now()
            if not is_commit_hash(revision):
                store.aliases[(org, model, revision)] = real
        return {
            "success": True,
            "commitOid": real,
            "commitUrl": f"{state.base_url}/{org}/{model}/commit/{real}",
            "hookOutput": "",
        }

    # --- reading -----------------------------------------------------------------------------
    def version_or_404(org: str, model: str, revision: str):
        version = store.get(org, model, revision)
        if version is None:
            kind = "RevisionNotFound" if (org, model) in store.repos else "RepoNotFound"
            return None, not_found(kind)
        return version, None

    @app.get(HF + "/api/models/{org}/{model}")
    @app.get(HF + "/api/models/{org}/{model}/revision/{revision}")
    async def model_info(repo_key: str, org: str, model: str, revision: str = "main"):
        if (bad := check_repo(repo_key)) is not None:
            return bad
        version, missing = version_or_404(org, model, revision)
        if missing:
            return missing
        return {
            "id": f"{org}/{model}",
            "modelId": f"{org}/{model}",
            "sha": version.revision,
            "private": False,
            "tags": [],
            "siblings": [{"rfilename": f.path} for f in version.files.values()],
        }

    @app.get(HF + "/api/models/{org}/{model}/tree/{revision}")
    @app.get(HF + "/api/models/{org}/{model}/tree/{revision}/{subpath:path}")
    async def tree(repo_key: str, org: str, model: str, revision: str, subpath: str = ""):
        if (bad := check_repo(repo_key)) is not None:
            return bad
        version, missing = version_or_404(org, model, revision)
        if missing:
            return missing
        out = []
        for f in version.files.values():
            entry = {"type": "file", "oid": f.sha256, "size": f.size, "path": f.path}
            if f.transfer == "large-file":
                entry["lfs"] = {"oid": f.sha256, "size": f.size, "pointerSize": 134}
            out.append(entry)
        return out

    @app.post(HF + "/api/models/{org}/{model}/paths-info/{revision}")
    async def paths_info(repo_key: str, org: str, model: str, revision: str, request: Request):
        if (bad := check_repo(repo_key)) is not None:
            return bad
        version, missing = version_or_404(org, model, revision)
        if missing:
            return missing
        body = await request.json()
        wanted = body.get("paths", [])
        out = []
        for path in wanted:
            f = version.files.get(path)
            if f is not None:
                entry = {"type": "file", "oid": f.sha256, "size": f.size, "path": f.path}
                if f.transfer == "large-file":
                    entry["lfs"] = {"oid": f.sha256, "size": f.size, "pointerSize": 134}
                out.append(entry)
        return out

    async def _serve(
        repo_key: str, org: str, model: str, revision: str, path: str, head: bool, request: Request
    ):
        if (bad := check_repo(repo_key)) is not None:
            return bad
        version, missing = version_or_404(org, model, revision)
        if missing:
            return missing
        f = version.files.get(path)
        if f is None:
            return not_found("EntryNotFound")
        headers = {
            "ETag": f'"{f.sha256}"',
            "X-Repo-Commit": version.revision,
            "Content-Length": str(f.size),
            "Accept-Ranges": "bytes",
        }
        if f.transfer == "large-file":
            headers["X-Linked-Size"] = str(f.size)
            headers["X-Linked-Etag"] = f'"{f.sha256}"'
        if head:
            return Response(status_code=200, headers=headers)
        if f.mode != "kept" or f.data is None:
            return error(501, "content_not_kept", "The stand-in did not keep this file's content.")
        switch: Switch | None = request.state.switch
        cut = switch is not None and switch.kind == "cut-transfer"
        return StreamingResponse(
            _read(f.data, f.size // 2 if cut else None),
            headers=headers,
            media_type="application/octet-stream",
        )

    @app.get(HF + "/{org}/{model}/resolve/{revision}/{path:path}")
    async def resolve_get(
        repo_key: str, org: str, model: str, revision: str, path: str, request: Request
    ):
        return await _serve(repo_key, org, model, revision, path, False, request)

    @app.head(HF + "/{org}/{model}/resolve/{revision}/{path:path}")
    async def resolve_head(
        repo_key: str, org: str, model: str, revision: str, path: str, request: Request
    ):
        return await _serve(repo_key, org, model, revision, path, True, request)

    # --- Artifactory's own storage-style listing and delete ----------------------------------
    @app.get("/artifactory/api/storage/{repo_key}/{path:path}")
    async def storage_list(repo_key: str, path: str = ""):
        if (bad := check_repo(repo_key)) is not None:
            return bad
        prefix = "/" + path.strip("/")
        files = []
        with store.lock:
            for v in store.versions.values():
                if v.state != "complete":
                    continue
                for f in v.files.values():
                    uri = store.file_uri(v, f.path)
                    if prefix == "/" or uri.startswith(prefix + "/"):
                        files.append(
                            {
                                "uri": uri,
                                "size": f.size,
                                "folder": False,
                                "sha256": f.sha256,
                                "sha2": f.sha256,
                            }
                        )
        if not files:
            return not_found()
        return {"uri": prefix, "files": sorted(files, key=lambda x: x["uri"])}

    @app.delete("/artifactory/{repo_key}/{path:path}")
    async def delete(repo_key: str, path: str):
        if (bad := check_repo(repo_key)) is not None:
            return bad
        target = path.strip("/")
        with store.lock:
            found = False
            for key, v in list(store.versions.items()):
                if store.version_dir(v.organisation, v.model, v.revision) == target:
                    del store.versions[key]
                    found = True
            for key, real in list(store.aliases.items()):
                if (key[0], key[1], real) not in store.versions:
                    del store.aliases[key]
        if not found:
            return not_found()
        return Response(status_code=204)

    # --- test-only control address (not part of the imitated surface) ------------------------
    @app.get("/__control/calls")
    async def control_calls(request: Request):
        if request.headers.get("authorization") != f"Bearer {state.token}":
            return error(401, "unauthorised", "A valid token is required.")
        return state.calls

    @app.post("/__control/switches")
    async def control_switch(request: Request):
        if request.headers.get("authorization") != f"Bearer {state.token}":
            return error(401, "unauthorised", "A valid token is required.")
        body = await request.json()
        switch = state.switches.add(body.pop("kind"), **body)
        return {"id": switch.id}

    @app.delete("/__control/switches")
    async def control_clear(request: Request):
        if request.headers.get("authorization") != f"Bearer {state.token}":
            return error(401, "unauthorised", "A valid token is required.")
        state.switches.clear()
        return Response(status_code=204)

    @app.exception_handler(StarletteHTTPException)
    async def unknown(request: Request, exc):
        return error(404, "not_imitated", f"The stand-in does not imitate {request.url.path}.")

    return app


class _null:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


async def _read(path: Path, limit: int | None):
    sent = 0
    with path.open("rb") as f:
        while True:
            chunk = f.read(BLOCK)
            if not chunk:
                return
            if limit is not None and sent + len(chunk) > limit:
                yield chunk[: limit - sent]
                raise RuntimeError("imitated: the transfer was cut")
            sent += len(chunk)
            yield chunk
            await asyncio.sleep(0)


_UNUSED = (re, time)
