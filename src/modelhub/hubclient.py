"""The only code that talks to Hugging Face. Everything else uses the small `HubClient`
interface, so tests can stand in a fake server (see tests/conftest.py)."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

ENDPOINT = "https://huggingface.co"
REQUEST_TIMEOUT = 30  # seconds; every request has a time limit (NFR5.3)


class HubError(Exception):
    """Anything that goes wrong while talking to Hugging Face."""


class TransientHubError(HubError):
    """A failure worth retrying: network trouble, a server error, a timeout."""


class RateLimited(TransientHubError):
    """Hugging Face asked us to slow down; `retry_after` is how long to wait, if it said."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class ModelNotFound(HubError):
    """No such model."""


class UnsupportedModel(HubError):
    """A private or gated model, which the first version does not handle (FR1.4)."""


class HubClient(Protocol):
    def model_info(self, repo_id: str, revision: str = "main") -> dict: ...

    def tree(self, repo_id: str, revision: str) -> list[dict]: ...

    def commits(self, repo_id: str, revision: str) -> list[dict]: ...

    def refs(self, repo_id: str) -> dict: ...

    def download_file(
        self,
        repo_id: str,
        revision: str,
        path: str,
        dest: Path,
        progress_cb: Callable[[int], None] | None = None,
    ) -> None: ...

    def read_file(self, repo_id: str, revision: str, path: str) -> bytes: ...


def _retry_after(headers) -> float | None:
    for name in ("Retry-After", "RateLimit"):
        value = headers.get(name)
        if not value:
            continue
        match = re.search(r"(?:t=|^)(\d+(?:\.\d+)?)", value)
        if match:
            return float(match.group(1))
    return None


class HfHubClient:
    """Talks to the real Hub through Hugging Face's own library: its HTTP session for the
    documented endpoints, and its download function (with the fast-transfer route) for files."""

    def __init__(self, token: str | None = None, endpoint: str = ENDPOINT, tqdm_class=None):
        self.token = token or os.environ.get("HF_TOKEN") or None
        self.endpoint = endpoint.rstrip("/")
        self.tqdm_class = tqdm_class
        # Usage reporting is off by default (NFR6.3).
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        os.environ.setdefault("HF_HUB_DISABLE_UPDATE_CHECK", "1")

    # --- web interface of the Hub -------------------------------------------------------

    def _get(self, url: str, params: dict | None = None):
        from huggingface_hub.utils import build_hf_headers, get_session

        try:
            response = get_session().get(
                url,
                params=params,
                headers=build_hf_headers(token=self.token),
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True,
            )
        except Exception as error:  # network trouble of every kind is worth a retry
            raise TransientHubError(f"{url}: {error}") from error
        self._raise_for_status(response, url)
        return response

    @staticmethod
    def _raise_for_status(response, url: str) -> None:
        status = response.status_code
        if status < 400:
            return
        if status == 404:
            raise ModelNotFound(url)
        if status in (401, 403):
            # Without a login the Hub answers 401 for a model that does not exist as well as
            # for one that is private or gated, so it cannot be told which.
            raise UnsupportedModel(f"{url}: not found, or private or gated (HTTP {status})")
        if status == 429:
            raise RateLimited(f"{url}: rate limited", _retry_after(response.headers))
        if status >= 500:
            raise TransientHubError(f"{url}: HTTP {status}")
        raise HubError(f"{url}: HTTP {status}")

    def _paged(self, url: str, params: dict | None = None) -> list:
        items: list = []
        next_url, next_params = url, params
        while next_url:
            response = self._get(next_url, next_params)
            items.extend(response.json())
            link = response.links.get("next") if hasattr(response, "links") else None
            next_url, next_params = (link["url"], None) if link else (None, None)
        return items

    def model_info(self, repo_id: str, revision: str = "main") -> dict:
        path = f"/api/models/{repo_id}" + ("" if revision == "main" else f"/revision/{revision}")
        return self._get(self.endpoint + path).json()

    def tree(self, repo_id: str, revision: str) -> list[dict]:
        url = f"{self.endpoint}/api/models/{repo_id}/tree/{revision}"
        return self._paged(url, {"recursive": "true", "expand": "true"})

    def commits(self, repo_id: str, revision: str) -> list[dict]:
        return self._paged(f"{self.endpoint}/api/models/{repo_id}/commits/{revision}")

    def refs(self, repo_id: str) -> dict:
        return self._get(f"{self.endpoint}/api/models/{repo_id}/refs").json()

    def read_file(self, repo_id: str, revision: str, path: str) -> bytes:
        return self._get(f"{self.endpoint}/{repo_id}/resolve/{revision}/{path}").content

    # --- file downloads (official library, fast-transfer route) ------------------------

    def download_file(self, repo_id, revision, path, dest: Path, progress_cb=None) -> None:
        from huggingface_hub import hf_hub_download

        scratch = dest.parent / ".modelhub-dl"
        reported = {"bytes": 0}

        def count(n: int) -> None:
            reported["bytes"] += n
            if progress_cb:
                progress_cb(n)

        try:
            local = hf_hub_download(
                repo_id,
                path,
                revision=revision,
                local_dir=scratch,
                token=self.token,
                endpoint=self.endpoint,
                tqdm_class=_progress_bar_class(count) if progress_cb else self.tqdm_class,
            )
        except Exception as error:
            raise _map_download_error(error) from error
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(local, dest)
        if progress_cb:  # make the total exact whatever the library did or did not report
            delta = dest.stat().st_size - reported["bytes"]
            if delta:
                progress_cb(delta)


def _progress_bar_class(callback):
    """A silent stand-in for the library's progress bar that passes byte counts on, so the
    live display moves while a big file is still downloading (NFR1.5)."""
    from tqdm.auto import tqdm

    class Bridge(tqdm):
        def __init__(self, *args, **kwargs):
            kwargs["disable"] = True
            super().__init__(*args, **kwargs)

        def update(self, n=1):
            if n:
                callback(int(n))

    return Bridge


def _map_download_error(error: Exception) -> HubError:
    name = type(error).__name__
    status = getattr(getattr(error, "response", None), "status_code", None)
    if (
        name
        in (
            "RepositoryNotFoundError",
            "RevisionNotFoundError",
            "EntryNotFoundError",
            "RemoteEntryNotFoundError",
        )
        or status == 404
    ):
        return ModelNotFound(str(error))
    if name == "GatedRepoError" or status in (401, 403):
        return UnsupportedModel(str(error))
    if status == 429:
        headers = getattr(error.response, "headers", {})
        return RateLimited(str(error), _retry_after(headers))
    return TransientHubError(str(error))
