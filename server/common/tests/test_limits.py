"""Speed, network and upkeep targets of the shared library (loop-back 2).

Checks NFR5.9 (token check under 5 ms with a cached key), NFR8.1 (no connection outside the
machine) and NFR5.11 (Dependabot stays on).
"""

import ipaddress
import socket
import time
from pathlib import Path

import pytest
from modelhub_common.keys import KeySet
from modelhub_common.tokens import Reason, TokenVerifier

ROOT = Path(__file__).parents[3]


@pytest.fixture
def verifier(issuer, clock):
    keys = KeySet(issuer.jwks, clock=clock)
    keys.load()
    return TokenVerifier(keys, issuer=issuer.issuer, audience=issuer.audience)


def test_a_check_with_a_cached_key_takes_under_5_ms_at_the_95th_percentile(verifier, issuer):
    token = issuer.token(sub="u1", username="ada")
    assert verifier.verify(token).valid  # warm up
    times = []
    for _ in range(300):
        began = time.perf_counter()
        assert verifier.verify(token).reason is Reason.OK
        times.append(time.perf_counter() - began)
    times.sort()
    assert times[int(len(times) * 0.95) - 1] < 0.005


def test_with_every_outside_socket_blocked_checks_still_work(verifier, issuer, monkeypatch):
    refused = []
    real = socket.socket.connect

    def guarded(self, address):
        host = address[0] if isinstance(address, tuple) else None
        if host is not None and not ipaddress.ip_address(socket.gethostbyname(host)).is_loopback:
            refused.append(address)
            raise OSError(f"blocked: {address}")
        return real(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    assert verifier.verify(issuer.token()).valid
    assert verifier.verify("a.b.c").reason is not Reason.OK
    assert refused == []


def test_dependabot_is_configured_for_every_python_package_and_the_workflows():
    text = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert "package-ecosystem: github-actions" in text
    projects = [ROOT, *sorted((ROOT / "server").glob("*/pyproject.toml"))]
    for item in projects:
        folder = item if item == ROOT else item.parent
        rel = "/" + folder.relative_to(ROOT).as_posix() if folder != ROOT else "/"
        assert f'directory: "{rel}"' in text, rel
