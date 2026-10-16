"""The portal's calls to the import service's retention and key routes (contract C4).

Always with the signed-in person's own token; the service checks the administrator role again.
"""

from __future__ import annotations

import httpx

from modelhub_portal.catalog_client import TokenRejected


class ServiceDown(Exception):
    """The retention and key service could not be reached (rule BR1.11)."""


class ServiceRefused(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class RetentionService:
    def __init__(self, http: httpx.Client, base_url: str = "") -> None:
        self._http, self._base = http, base_url.rstrip("/")

    def _call(self, token: str, method: str, path: str, rid: str | None, **kw) -> httpx.Response:
        headers = {"Authorization": f"Bearer {token}"}
        if rid:
            headers["X-Request-Id"] = rid
        try:
            r = self._http.request(method, self._base + path, headers=headers, **kw)
        except httpx.HTTPError as exc:
            raise ServiceDown("The retention service cannot be reached.") from exc
        if r.status_code >= 500:
            raise ServiceDown("The retention service cannot be reached.")
        if r.status_code == 401:
            raise TokenRejected()
        return r

    @staticmethod
    def _refused(r: httpx.Response) -> ServiceRefused:
        try:
            body = r.json()
        except ValueError:
            body = {}
        return ServiceRefused(r.status_code, body.get("code", "refused"), body.get("message", ""))

    def _json(self, r: httpx.Response, ok=(200, 201)) -> dict:
        if r.status_code not in ok:
            raise self._refused(r)
        return r.json()

    # -- retention ------------------------------------------------------------------------
    def settings(self, token: str, rid=None) -> dict:
        return self._json(self._call(token, "GET", "/v1/retention/settings", rid))

    def set_period(self, token: str, days: int, rid=None) -> dict:
        r = self._call(token, "PUT", "/v1/retention/settings", rid, json={"periodDays": days})
        return self._json(r)

    def due(self, token: str, rid=None) -> list[dict]:
        return self._json(self._call(token, "GET", "/v1/retention/due", rid))["items"]

    def decisions(self, token: str, rid=None) -> list[dict]:
        return self._json(self._call(token, "GET", "/v1/retention/decisions", rid))["items"]

    def decide(self, token: str, model: str, commit: str, decision: str, rid=None) -> dict:
        body = {"modelId": model, "commit": commit, "decision": decision}
        return self._json(self._call(token, "POST", "/v1/retention/decisions", rid, json=body))

    # -- trusted keys ---------------------------------------------------------------------
    def keys(self, token: str, rid=None) -> list[dict]:
        return self._json(self._call(token, "GET", "/v1/trusted-keys", rid))["items"]

    def add_key(self, token: str, public_key: str, fingerprint: str, name: str, rid=None) -> dict:
        body = {"publicKey": public_key, "typedFingerprint": fingerprint, "name": name}
        return self._json(self._call(token, "POST", "/v1/trusted-keys", rid, json=body))

    def remove_key(self, token: str, key_id: str, rid=None) -> None:
        r = self._call(token, "DELETE", f"/v1/trusted-keys/{key_id}", rid)
        if r.status_code != 204:
            raise self._refused(r)
