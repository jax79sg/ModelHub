"""A TCP relay that can be switched off and on, to imitate a dependency going away and back.

While off it accepts a connection and drops it at once, so the program under test sees a server
that is away; switched on, it passes connections through to the real address again.
"""

from __future__ import annotations

import socket
import threading


class Relay:
    def __init__(self, host: str, port: int) -> None:
        self.target = (host, port)
        self.up = False
        self._live: list[socket.socket] = []
        self._server = socket.socket()
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(50)
        self.port = self._server.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True).start()

    def start(self) -> None:
        self.up = True

    def stop(self) -> None:
        self.up = False
        for s in self._live:
            _shut(s)
        self._live.clear()

    def close(self) -> None:
        self.stop()
        self._server.close()

    def _accept(self) -> None:
        while True:
            try:
                client, _ = self._server.accept()
            except OSError:
                return
            if not self.up:
                client.close()
                continue
            try:
                upstream = socket.create_connection(self.target, timeout=5)
            except OSError:
                client.close()
                continue
            self._live += [client, upstream]
            for a, b in ((client, upstream), (upstream, client)):
                threading.Thread(target=_pipe, args=(a, b), daemon=True).start()


def _shut(sock: socket.socket) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    sock.close()


def _pipe(src: socket.socket, dst: socket.socket) -> None:
    try:
        while data := src.recv(65536):
            dst.sendall(data)
    except OSError:
        pass
    finally:
        _shut(src)
        _shut(dst)
