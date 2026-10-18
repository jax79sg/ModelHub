"""The service's client of the Catalog, and how it gets its own token (contracts C2, C3, C6).

The Catalog is the only reader and writer of model information (ADR-002), so everything the
import and retention steps need to know or record goes through here. The service identifies
itself to the Catalog with a Keycloak token obtained by client credentials.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import httpx

TOKEN_MARGIN_SECONDS = 30


class CatalogUnavailable(Exception):
    """The Catalog could not be reached or answered with a server error (retryable)."""


class CatalogConflict(Exception):
    """A different record already exists for this model and commit."""


class CatalogInvalid(Exception):
    """The Catalog refused the record as invalid."""


class AuthUnavailable(Exception):
    """The service cannot obtain or use its own token (never carries a secret)."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ServiceTokenProvider:
    """Gets a Keycloak token for this service's client by client credentials and caches it."""

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: Callable[[], str],
        http: httpx.Client | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._url, self._client_id, self._secret = token_url, client_id, client_secret
        self._http = http or httpx.Client(timeout=httpx.Timeout(30, connect=5))
        self._clock = clock
        self._token: str | None = None
        self._expires: datetime | None = None
        self._lock = threading.Lock()

    def __call__(self) -> str:
        with self._lock:
            now = self._clock()
            if self._token and self._expires and now < self._expires:
                return self._token
            try:
                response = self._http.post(
                    self._url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._client_id,
                        "client_secret": self._secret(),
                    },
                )
            except httpx.HTTPError as exc:
                raise AuthUnavailable("The sign-in service could not be reached.") from exc
            if response.status_code != 200:
                raise AuthUnavailable(
                    f"The sign-in service refused the service token ({response.status_code})."
                )
            body = response.json()
            self._token = body["access_token"]
            lifetime = int(body.get("expires_in", 60))
            self._expires = now + timedelta(seconds=max(lifetime - TOKEN_MARGIN_SECONDS, 1))
            return self._token


class CatalogClient:
    def __init__(self, http: httpx.Client, base_url: str, token: Callable[[], str]) -> None:
        self._http, self._base, self._token = http, base_url.rstrip("/"), token

    def _request(self, method: str, path: str, **kw) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self._token()}"}
        try:
            response = self._http.request(method, self._base + path, headers=headers, **kw)
        except httpx.HTTPError as exc:
            raise CatalogUnavailable("The Catalog could not be reached.") from exc
        if response.status_code >= 500:
            raise CatalogUnavailable(f"The Catalog answered {response.status_code}.")
        if response.status_code in (401, 403):
            raise AuthUnavailable("The Catalog did not accept this service's token.")
        return response

    def ping(self) -> bool:
        """True when the Catalog's live check answers (no token is needed or sent)."""
        try:
            return self._http.get(self._base + "/healthz").status_code == 200
        except httpx.HTTPError:
            return False

    def introspect(self, token_value: str) -> dict:
        r = self._request("POST", "/v1/tokens/introspect", json={"token": token_value})
        return r.json()

    def get_version(self, model_id: str, commit: str) -> dict | None:
        r = self._request("GET", f"/v1/models/{model_id}/versions/{commit}")
        return None if r.status_code == 404 else r.json()

    def put_version(
        self,
        model_id: str,
        commit: str,
        record: dict,
        documents: list[tuple[str, bytes, str]],
    ) -> str:
        files = [("documents", (name, data, ctype)) for name, data, ctype in documents]
        r = self._request(
            "PUT",
            f"/v1/models/{model_id}/versions/{commit}",
            data={"record": json.dumps(record)},
            files=files or None,
        )
        return self._put_result(r)

    def put_import_only(self, model_id: str, commit: str, record: dict) -> str:
        r = self._request(
            "PUT", f"/v1/models/{model_id}/versions/{commit}", data={"record": json.dumps(record)}
        )
        return self._put_result(r)

    @staticmethod
    def _put_result(r: httpx.Response) -> str:
        if r.status_code in (200, 201):
            return r.json()["status"]
        if r.status_code == 409:
            raise CatalogConflict("record_conflict")
        if r.status_code == 422:
            raise CatalogInvalid(r.json().get("message", "invalid record"))
        raise CatalogUnavailable(f"The Catalog answered {r.status_code}.")

    def mark_removed(self, model_id: str, commit: str, removed_by: str) -> str:
        r = self._request(
            "POST",
            f"/v1/models/{model_id}/versions/{commit}/removal",
            json={"removedBy": removed_by},
        )
        return "ok" if r.status_code == 200 else "conflict"

    def versions(
        self,
        state: str | None = None,
        imported_before: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict:
        params = {"page": page, "pageSize": page_size}
        if state:
            params["state"] = state
        if imported_before:
            params["importedBefore"] = imported_before
        return self._request("GET", "/v1/versions", params=params).json()


_ = time
