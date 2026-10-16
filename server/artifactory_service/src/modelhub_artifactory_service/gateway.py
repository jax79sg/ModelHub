"""The only caller of Artifactory (rules BR1.3, BR1.7, BR1.19; contract C5).

* Storage locations of a version are **discovered by listing**, never composed from a layout
  assumption (open item X1): the listing is read under ``<org>/<model>``, then under
  ``models/<org>/<model>`` (the layout JFrog's examples show), then in the whole repository, and a
  version's files are the entries that have the organisation, the model and then the revision in
  their path.
* Uploads go through an ``Uploader``: the JFrog CLI in production, the Hugging Face client in
  tests. Neither is ever asked to overwrite.
* The credential is held here only. It is passed to the upload tool through its environment and
  never put on a command line, in a log line, in an error message or in what is returned.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import httpx

log = logging.getLogger("modelhub.gateway")


class ArtifactoryUnreachable(Exception):
    """Artifactory could not be reached or answered with a server error (retryable)."""


class UploadError(Exception):
    code = "artifactory_refused"
    retryable = False

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UploadConflict(UploadError):
    code = "artifactory_conflict"


class UploadRefused(UploadError):
    code = "artifactory_refused"


class UploadNetworkError(UploadError):
    code = "artifactory_unreachable"
    retryable = True


@dataclass
class VersionListing:
    state: str  # absent | present | complete | inconsistent
    files: dict[str, tuple[int, str | None]] = field(default_factory=dict)
    differences: list[str] = field(default_factory=list)
    directory: str | None = None


class Uploader(Protocol):
    def upload(self, folder: Path, model_id: str, revision: str) -> None: ...


def _endpoint(base_url: str, repo_key: str) -> str:
    return f"{base_url.rstrip('/')}/artifactory/api/huggingfaceml/{repo_key}"


# --------------------------------------------------------------------------- uploaders ---------
class HfUploader:
    """Uploads with the Hugging Face client (what ``jf hf upload`` wraps)."""

    def __init__(self, base_url: str, repo_key: str, token: str) -> None:
        self._endpoint = _endpoint(base_url, repo_key)
        self._token = token

    def upload(self, folder: Path, model_id: str, revision: str) -> None:
        from huggingface_hub import HfApi

        api = HfApi(endpoint=self._endpoint, token=self._token)
        try:
            api.create_repo(model_id, exist_ok=True)
            api.upload_folder(repo_id=model_id, folder_path=str(folder), revision=revision)
        except Exception as exc:  # noqa: BLE001 - every failure is classified below
            raise _classify_hf(exc) from None


def _chain(exc: BaseException):
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        yield exc
        exc = exc.__cause__ or exc.__context__


def _classify_hf(exc: BaseException) -> UploadError:
    for item in _chain(exc):
        response = getattr(item, "response", None)
        status = getattr(response, "status_code", None)
        if status == 409:
            return UploadConflict("Artifactory already holds this version.")
        if status is not None and (status >= 500 or status == 429):
            return UploadNetworkError(f"Artifactory answered {status}.")
        if status is not None and status in (401, 403):
            return UploadRefused("Artifactory refused the credential or the permission.")
        if status is not None and status >= 400:
            return UploadRefused(f"Artifactory refused the upload ({status}).")
        if isinstance(item, httpx.TransportError | OSError | TimeoutError):
            return UploadNetworkError("Artifactory could not be reached.")
    return UploadRefused("The upload was refused.")


_CONFLICT = re.compile(r"\b409\b|conflict", re.IGNORECASE)
_NETWORK = re.compile(
    r"connection\s?(error|refused|reset|aborted)|max retries|timed? ?out|timeout|"
    r"\b50[234]\b|service unavailable|temporarily|name resolution|remote end closed",
    re.IGNORECASE,
)


class JfUploader:
    """Uploads with ``jf hf upload`` (JFrog's documented command).

    The credential goes in the environment (``HF_TOKEN``), the address in ``HF_ENDPOINT``; neither
    is ever on the command line. The tool's own output is classified (409, network, other) and
    then discarded: it is never returned, because it can echo a credential."""

    def __init__(
        self,
        base_url: str,
        repo_key: str,
        token: str,
        jf_path: str = "jf",
        timeout: float | None = None,
    ) -> None:
        self._base, self._key, self._token = base_url.rstrip("/"), repo_key, token
        self._jf, self._timeout = jf_path, timeout

    def upload(self, folder: Path, model_id: str, revision: str) -> None:
        argv = [
            self._jf,
            "hf",
            "upload",
            str(folder),
            model_id,
            f"--revision={revision}",
            f"--repo-key={self._key}",
            "--repo-type=model",
        ]
        env = dict(os.environ)
        env.update(
            HF_ENDPOINT=_endpoint(self._base, self._key),
            HF_TOKEN=self._token,
            HF_HUB_DISABLE_TELEMETRY="1",
            JFROG_CLI_AVOID_NEW_VERSION_WARNING="true",
            JFROG_CLI_REPORT_USAGE="false",
            CI="true",
        )
        try:
            done = subprocess.run(
                argv, env=env, capture_output=True, text=True, timeout=self._timeout, check=False
            )
        except FileNotFoundError:
            raise UploadRefused("The JFrog CLI (jf) is not installed in this container.") from None
        except subprocess.TimeoutExpired:
            raise UploadNetworkError("The upload made no progress in time.") from None
        if done.returncode == 0:
            return
        text = (done.stderr or "") + "\n" + (done.stdout or "")
        if _CONFLICT.search(text):
            raise UploadConflict("Artifactory already holds this version.")
        if _NETWORK.search(text):
            raise UploadNetworkError("Artifactory could not be reached or is busy.")
        log.warning(
            "upload refused", extra={"event": "upload_refused", "exit_code": done.returncode}
        )
        raise UploadRefused("Artifactory refused the upload.")


# ----------------------------------------------------------------------------- gateway -------
class Gateway:
    def __init__(
        self,
        base_url: str,
        repo_key: str,
        token: str,
        http: httpx.Client | None = None,
        uploader: Uploader | None = None,
        connect_timeout: float = 5,
        read_timeout: float = 30,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._key = repo_key
        self._token = token
        self._http = http or httpx.Client(
            timeout=httpx.Timeout(read_timeout, connect=connect_timeout)
        )
        self.uploader: Uploader = uploader or HfUploader(base_url, repo_key, token)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    # -- listing --------------------------------------------------------------------------------
    def _list_prefix(self, prefix: str) -> list[dict] | None:
        """Every file under a path of the repository, or None when that path does not exist."""
        url = f"{self._base}/artifactory/api/storage/{self._key}/{prefix}".rstrip("/")
        try:
            response = self._http.get(url, params={"list": "", "deep": 1}, headers=self._headers())
        except httpx.HTTPError as exc:
            raise ArtifactoryUnreachable("Artifactory could not be reached.") from exc
        if response.status_code == 404:
            return None
        if response.status_code in (401, 403):
            raise UploadRefused("Artifactory refused the credential or the permission.")
        if response.status_code >= 500:
            raise ArtifactoryUnreachable(f"Artifactory answered {response.status_code}.")
        response.raise_for_status()
        return response.json().get("files", [])

    def list_version(
        self,
        model_id: str,
        revision: str,
        expected: dict[str, tuple[int, str]] | None = None,
    ) -> VersionListing:
        """What Artifactory holds for one version, compared with ``expected`` when given."""
        org, _, model = model_id.partition("/")
        entries: list[dict] | None = None
        for prefix in (f"{org}/{model}", f"models/{org}/{model}", ""):
            entries = self._list_prefix(prefix)
            if entries is not None:
                break
        found, directory = self._version_files(entries or [], org, model, revision, expected)
        if not found:
            return VersionListing("absent")
        if expected is None:
            return VersionListing("present", found, [], directory)
        differences = []
        for path in sorted(set(expected) | set(found)):
            if path not in found:
                differences.append(f"missing: {path}")
            elif path not in expected:
                differences.append(f"extra: {path}")
            elif found[path][0] != expected[path][0] or (
                found[path][1] is not None and found[path][1] != expected[path][1]
            ):
                differences.append(f"differs: {path}")
        return VersionListing(
            "inconsistent" if differences else "complete", found, differences, directory
        )

    @staticmethod
    def _version_files(entries, org, model, revision, expected):
        found: dict[str, tuple[int, str | None]] = {}
        directory = None
        for entry in entries:
            parts = entry.get("uri", "").strip("/").split("/")
            start = next(
                (i for i in range(len(parts) - 1) if parts[i] == org and parts[i + 1] == model),
                None,
            )
            if start is None:
                continue
            at = next((j for j in range(start + 2, len(parts)) if parts[j] == revision), None)
            if at is None:
                continue
            rel = "/".join(parts[at + 1 :])
            if rel.startswith("files/") and (
                expected is None or (rel not in expected and rel[6:] in expected)
            ):
                rel = rel[6:]
            if not rel:
                continue
            found[rel] = (int(entry.get("size", 0)), entry.get("sha256") or entry.get("sha2"))
            directory = "/".join(parts[: at + 1])
        return found, directory

    # -- delete ---------------------------------------------------------------------------------
    def delete_version(self, listing: VersionListing) -> str:
        """Delete a listed version. ``deleted``, or ``gone`` when it was already not there."""
        if not listing.directory:
            return "gone"
        url = f"{self._base}/artifactory/{self._key}/{listing.directory}"
        try:
            response = self._http.delete(url, headers=self._headers())
        except httpx.HTTPError as exc:
            raise ArtifactoryUnreachable("Artifactory could not be reached.") from exc
        if response.status_code in (200, 202, 204):
            return "deleted"
        if response.status_code == 404:
            return "gone"
        if response.status_code in (401, 403):
            raise UploadRefused("Artifactory refused the credential or the permission.")
        if response.status_code >= 500:
            raise ArtifactoryUnreachable(f"Artifactory answered {response.status_code}.")
        raise UploadRefused(f"Artifactory refused the delete ({response.status_code}).")
