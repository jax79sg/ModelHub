"""The portal's calls to the Catalog, always with the person's own token (contracts C2, C3)."""

from __future__ import annotations

import httpx


class CatalogDown(Exception):
    """The Catalog could not be reached or answered with a server error (rule BR1.11)."""


class TokenRejected(Exception):
    """The Catalog did not accept the person's access token."""


class CatalogRefused(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class Gone(Exception):
    """The document was removed with its version."""


class Catalog:
    def __init__(self, http: httpx.Client, base_url: str = "") -> None:
        self._http, self._base = http, base_url.rstrip("/")

    def _call(self, token: str, method: str, path: str, rid: str | None, **kw) -> httpx.Response:
        headers = {"Authorization": f"Bearer {token}"}
        if rid:
            headers["X-Request-Id"] = rid
        try:
            r = self._http.request(method, self._base + path, headers=headers, **kw)
        except httpx.HTTPError as exc:
            raise CatalogDown("The model database cannot be reached.") from exc
        if r.status_code >= 500:
            raise CatalogDown("The model database cannot be reached.")
        if r.status_code == 401:
            raise TokenRejected()
        return r

    @staticmethod
    def _refused(r: httpx.Response) -> CatalogRefused:
        try:
            body = r.json()
        except ValueError:
            body = {}
        return CatalogRefused(r.status_code, body.get("code", "refused"), body.get("message", ""))

    def models(self, token: str, params: dict, rid: str | None = None) -> dict:
        r = self._call(token, "GET", "/v1/models", rid, params=params)
        if r.status_code != 200:
            raise self._refused(r)
        return r.json()

    def model(self, token: str, model_id: str, rid: str | None = None) -> dict | None:
        r = self._call(token, "GET", f"/v1/models/{model_id}", rid)
        return None if r.status_code == 404 else r.json()

    def version(self, token: str, model_id: str, commit: str, rid: str | None = None):
        r = self._call(token, "GET", f"/v1/models/{model_id}/versions/{commit}", rid)
        return None if r.status_code == 404 else r.json()

    def document(self, token: str, model_id: str, commit: str, kind: str, name: str, rid=None):
        path = f"/v1/models/{model_id}/versions/{commit}/documents/{kind}/{name}"
        r = self._call(token, "GET", path, rid)
        if r.status_code == 410:
            raise Gone()
        if r.status_code != 200:
            return None
        return r.content, r.headers.get("content-type", "application/octet-stream")

    def make_token(self, token: str, name: str, rid: str | None = None) -> dict:
        r = self._call(token, "POST", "/v1/tokens", rid, json={"name": name})
        if r.status_code != 201:
            raise self._refused(r)
        return r.json()

    def list_tokens(self, token: str, everyone: bool = False, rid: str | None = None) -> list[dict]:
        r = self._call(token, "GET", "/v1/tokens", rid, params={"all": "true"} if everyone else {})
        if r.status_code != 200:
            raise self._refused(r)
        return r.json()["items"]

    def revoke_token(self, token: str, token_id: str, rid: str | None = None) -> bool:
        r = self._call(token, "DELETE", f"/v1/tokens/{token_id}", rid)
        return r.status_code == 204
