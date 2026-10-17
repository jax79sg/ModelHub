"""Start the stand-in inside a test run, on a free local port (rule BR1.14).

It binds 127.0.0.1 only, starts empty, takes its token from the caller (never from the
environment), and removes its temporary folder when it stops.
"""

from __future__ import annotations

import shutil
import tempfile
import threading
import time
from pathlib import Path

import httpx
import uvicorn

from .app import State, create_app
from .store import LAYOUTS, Store, StoredFile
from .switches import Switch

LOCAL = "127.0.0.1"


class StandIn:
    def __init__(
        self,
        token: str,
        repo_key: str = "models-hf",
        layout: str = "flat",
        keep_limit_bytes: int = 1024 * 1024,
        write_allowed: bool = True,
        overwrite_allowed: bool = False,
        workdir: Path | str | None = None,
        host: str = LOCAL,
        port: int = 0,
        allow_any_host: bool = False,
        public_host: str | None = None,
    ) -> None:
        if host != LOCAL and not allow_any_host:
            raise ValueError("the stand-in only listens on the local machine")
        self._host = host
        self._public_host = public_host or (LOCAL if host in (LOCAL, "0.0.0.0") else host)
        if layout not in LAYOUTS:
            raise ValueError(f"layout must be one of {LAYOUTS}")
        if not token:
            raise ValueError("a token is required")
        self._own_workdir = workdir is None
        self.workdir = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="stand-in-"))
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.token = token
        self.repo_key = repo_key
        self.store = Store(self.workdir, keep_limit_bytes, layout)
        self.store.write_allowed = write_allowed
        self.store.overwrite_allowed = overwrite_allowed
        self.state = State(token, repo_key, self.store)
        self._port = port
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self.url = ""

    # --- lifecycle ---------------------------------------------------------------------------
    def start(self) -> StandIn:
        config = uvicorn.Config(
            create_app(self.state),
            host=self._host,
            port=self._port,
            log_level="warning",
            lifespan="off",
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        deadline = time.monotonic() + 20
        while not self._server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("the stand-in did not start")
            time.sleep(0.01)
        port = self._server.servers[0].sockets[0].getsockname()[1]
        self.url = f"http://{self._public_host}:{port}"
        self.state.base_url = self.url
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=10)
        shutil.rmtree(self.workdir, ignore_errors=True) if self._own_workdir else shutil.rmtree(
            self.store.content, ignore_errors=True
        )

    def __enter__(self) -> StandIn:  # noqa: PYI034 - Self needs Python 3.11
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    # --- addresses ---------------------------------------------------------------------------
    @property
    def hf_endpoint(self) -> str:
        return f"{self.url}/artifactory/api/huggingfaceml/{self.repo_key}"

    # --- what a test can read and set --------------------------------------------------------
    @property
    def calls(self) -> list[dict]:
        return list(self.state.calls)

    def add_switch(self, kind: str, **kw) -> Switch:
        return self.state.switches.add(kind, **kw)

    def clear_switches(self) -> None:
        self.state.switches.clear()

    def set_write_allowed(self, value: bool) -> None:
        self.store.write_allowed = value

    def set_overwrite_allowed(self, value: bool) -> None:
        self.store.overwrite_allowed = value

    def mark_keep(self, path: str) -> None:
        self.store.keep_paths.add(path)

    def repositories(self) -> list[str]:
        return sorted(f"{o}/{m}" for o, m in self.store.repos)

    def _split(self, repo: str) -> tuple[str, str]:
        org, _, model = repo.partition("/")
        return org, model

    def version_state(self, repo: str, revision: str) -> str | None:
        org, model = self._split(repo)
        real = self.store.resolve(org, model, revision)
        version = self.store.versions.get((org, model, real))
        return version.state if version else None

    def version_files(self, repo: str, revision: str) -> list[StoredFile]:
        org, model = self._split(repo)
        version = self.store.get(org, model, revision, complete_only=False)
        return list(version.files.values()) if version else []

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def storage_list(self, repo: str, revision: str) -> dict:
        org, model = self._split(repo)
        real = self.store.resolve(org, model, revision)
        base = self.store.version_dir(org, model, real)
        r = httpx.get(
            f"{self.url}/artifactory/api/storage/{self.repo_key}/{base}",
            params={"list": "", "deep": 1},
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def storage_list_status(self, repo: str, revision: str) -> int:
        org, model = self._split(repo)
        real = self.store.resolve(org, model, revision)
        base = self.store.version_dir(org, model, real)
        r = httpx.get(
            f"{self.url}/artifactory/api/storage/{self.repo_key}/{base}",
            params={"list": "", "deep": 1},
            headers=self._headers(),
        )
        return r.status_code

    def delete_version(self, repo: str, revision: str) -> int:
        org, model = self._split(repo)
        real = self.store.resolve(org, model, revision)
        base = self.store.version_dir(org, model, real)
        r = httpx.delete(f"{self.url}/artifactory/{self.repo_key}/{base}", headers=self._headers())
        return r.status_code
