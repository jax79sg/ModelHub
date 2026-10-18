"""A stand-in for the import service's C1 interface, with switches for the failures to try."""

import hashlib
import json

import httpx


class FakeImportService:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []
        self.headers: list[dict] = []
        self.state = "receiving"
        self.stored: dict[int, str] = {}
        self.pieces_expected = 0
        self.skip = False
        self.create_error: tuple[int, dict] | None = None
        self.busy_starts = 0
        self.piece_failures: list[tuple[int, dict]] = []
        self.flaky = 0  # connection failures before the next request works
        self.polls_before_done = 1
        self.final: dict = {"state": "done", "outcome": "imported"}
        self.polled = 0
        self.bodies: list[dict] = []
        self.started = False

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    @staticmethod
    def _json(status, body):
        return httpx.Response(status, json=body)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        if self.flaky:
            self.flaky -= 1
            raise httpx.ConnectError("down")
        path = request.url.path
        self.calls.append((request.method, path))
        self.headers.append(dict(request.headers))
        if request.method == "POST" and path == "/v1/imports":
            body = json.loads(request.content)
            self.bodies.append(body)
            if self.create_error:
                return self._json(*self.create_error)
            description = json.loads(body["bundleDescription"])
            self.pieces_expected = len(description["pieces"])
            if self.skip:
                return self._json(200, {"importId": "i1", "state": "skipped", "outcome": "skipped"})
            missing = [n for n in range(1, self.pieces_expected + 1) if n not in self.stored]
            return self._json(
                201, {"importId": "i1", "state": "receiving", "missingPieces": missing}
            )
        if request.method == "PUT" and "/pieces/" in path:
            index = int(path.rsplit("/", 1)[1])
            if self.piece_failures:
                return self._json(*self.piece_failures.pop(0))
            data = request.read()
            digest = hashlib.sha256(data).hexdigest()
            if digest != request.headers["x-piece-sha256"]:
                return self._json(
                    409, {"code": "piece_mismatch", "message": "bad piece", "retryable": False}
                )
            self.stored[index] = digest
            return httpx.Response(204)
        if request.method == "POST" and path.endswith("/start"):
            if self.busy_starts:
                self.busy_starts -= 1
                return self._json(
                    503, {"code": "service_busy", "message": "busy", "retryable": True}
                )
            missing = [n for n in range(1, self.pieces_expected + 1) if n not in self.stored]
            if missing:
                return self._json(
                    409, {"code": "pieces_missing", "message": "missing", "retryable": False}
                )
            self.started = True
            return self._json(202, {"importId": "i1", "state": "verifying"})
        if request.method == "GET" and path == "/v1/imports/i1":
            self.polled += 1
            if self.polled < self.polls_before_done:
                return self._json(
                    200,
                    {
                        "importId": "i1",
                        "state": "uploading",
                        "progress": {"step": "uploading", "bytesDone": 5, "bytesTotal": 10},
                    },
                )
            return self._json(200, {"importId": "i1", **self.final})
        return httpx.Response(404)


def serve(fake: "FakeImportService", on_request=None):
    """Put the fake behind a real local HTTP port, so a separate process can call it.

    ``on_request(method, path)`` runs before each answer (a test uses it to kill the caller).
    Returns ``(url, stop)``.
    """
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def _answer(self):
            length = int(self.headers.get("content-length") or 0)
            body = self.rfile.read(length) if length else b""
            if on_request:
                on_request(self.command, self.path)
            request = httpx.Request(
                self.command,
                f"http://127.0.0.1{self.path}",
                headers=dict(self.headers),
                content=body,
            )
            response = fake._handle(request)
            self.send_response(response.status_code)
            data = response.content
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Type", response.headers.get("content-type", "text/plain"))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = do_PUT = do_DELETE = _answer

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def stop() -> None:
        server.shutdown()
        server.server_close()

    return f"http://127.0.0.1:{server.server_address[1]}", stop
