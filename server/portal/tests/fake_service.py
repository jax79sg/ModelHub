"""A stand-in for the import service's retention and key routes (contract C4)."""

import json

import httpx


class FakeService:
    def __init__(self):
        self.period = 365
        self.due = [
            {
                "modelId": "acme/old",
                "commit": "1" * 40,
                "importedAt": "2024-01-01T00:00:00Z",
                "importedBy": "ada",
                "sizeBytes": 2048,
                "ageDays": 800,
                "lastKeptAt": None,
            }
        ]
        self.decisions: list[dict] = []
        self.keys = [
            {
                "keyId": "k1",
                "fingerprint": "aaaa-bbbb",
                "name": "release key",
                "addedBy": "root",
                "addedAt": "2026-01-01T00:00:00Z",
                "status": "active",
            }
        ]
        self.calls: list[tuple[str, str]] = []
        self.auth: list[str] = []
        self.remove_outcome = {"outcome": "removed"}
        self.down = False
        self.add_error: tuple[int, dict] | None = None
        self.decide_status = 200
        self.admin = True

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("down")
        path, method = request.url.path, request.method
        self.calls.append((method, path))
        self.auth.append(request.headers.get("authorization", ""))
        body = json.loads(request.content) if request.content else {}
        if path == "/v1/retention/settings":
            if method == "PUT":
                if not self.admin:
                    return httpx.Response(403, json={"code": "forbidden", "message": "no"})
                days = body.get("periodDays")
                if not isinstance(days, int) or not 1 <= days <= 3650:
                    return httpx.Response(
                        422,
                        json={
                            "code": "invalid_period",
                            "message": "The period is a whole number of days, 1 to 3650.",
                        },
                    )
                self.period = days
            return httpx.Response(
                200, json={"periodDays": self.period, "changedBy": "root", "changedAt": None}
            )
        if not self.admin and (
            path.startswith("/v1/trusted-keys")
            or path == "/v1/retention/due"
            or (method == "POST" and path == "/v1/retention/decisions")
        ):
            return httpx.Response(403, json={"code": "forbidden", "message": "no"})
        if path == "/v1/retention/due":
            return httpx.Response(200, json={"items": self.due})
        if path == "/v1/retention/decisions" and method == "GET":
            return httpx.Response(200, json={"items": self.decisions})
        if path == "/v1/retention/decisions" and method == "POST":
            if self.decide_status != 200:
                return httpx.Response(
                    self.decide_status,
                    json={"code": "not_removable", "message": "Not an imported version."},
                )
            self.decisions.append(
                {
                    "decisionId": "d1",
                    "modelId": body["modelId"],
                    "commit": body["commit"],
                    "decision": body["decision"],
                    "decidedBy": "root",
                    "decidedAt": "2026-03-01T00:00:00Z",
                    "outcome": "done",
                    "message": None,
                }
            )
            return httpx.Response(
                200, json={"outcome": "kept"} if body["decision"] == "keep" else self.remove_outcome
            )
        if path == "/v1/trusted-keys" and method == "GET":
            return httpx.Response(200, json={"items": self.keys})
        if path == "/v1/trusted-keys" and method == "POST":
            if self.add_error:
                return httpx.Response(self.add_error[0], json=self.add_error[1])
            self.keys.append(
                {
                    "keyId": "k2",
                    "fingerprint": body["typedFingerprint"],
                    "name": body["name"],
                    "addedBy": "root",
                    "addedAt": "2026-03-01T00:00:00Z",
                    "status": "active",
                }
            )
            return httpx.Response(
                201,
                json={"keyId": "k2", "fingerprint": body["typedFingerprint"], "name": body["name"]},
            )
        if path.startswith("/v1/trusted-keys/") and method == "DELETE":
            for k in self.keys:
                if k["keyId"] == path.rsplit("/", 1)[1]:
                    k["status"] = "revoked"
            return httpx.Response(204)
        return httpx.Response(404)
