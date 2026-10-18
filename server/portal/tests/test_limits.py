"""Page time, page weight, sign-in time, load and network of the portal (loop-back 2).

Checks NFR2.1 to NFR2.4, NFR7.1 and NFR8.1 of the portal unit. Nothing here weakens a target.
"""

import ipaddress
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

import pytest
from conftest import BASE, sign_in
from modelhub_testkit.catalog_data import fill
from seed import PNG, put

C1 = "1" * 40


def p95(times: list[float]) -> float:
    times = sorted(times)
    return times[int(len(times) * 0.95) - 1]


@pytest.fixture
def big(catalog_http, fresh_database, keycloak, signed_in):
    fill(fresh_database, 1000)
    put(catalog_http, keycloak.issuer, "acme/tiny", C1, task="text-generation", downloads=10)
    return signed_in


LISTS = ["/models", "/models?task=text-generation", "/models?sort=likes", "/models?search=model-77"]


# --- NFR2.1, NFR2.2: page time at 1,000 models --------------------------------------------------
def test_the_list_answers_95_of_100_requests_under_a_second_at_1000_models(big):
    times = []
    for i in range(100):
        began = time.perf_counter()
        assert big.get(LISTS[i % len(LISTS)]).status_code == 200
        times.append(time.perf_counter() - began)
    assert sum(t < 1.0 for t in times) >= 95


def test_a_model_page_without_pictures_has_a_95th_percentile_under_a_second(big):
    times = []
    for _ in range(100):
        began = time.perf_counter()
        assert big.get("/acme/tiny").status_code == 200
        times.append(time.perf_counter() - began)
    assert p95(times) < 1.0


# --- NFR2.3: page weight and nothing from outside ----------------------------------------------
class _Assets(HTMLParser):
    """The files a page asks the browser to load (script, link and image tags)."""

    def __init__(self) -> None:
        super().__init__()
        self.found: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "link", "img"):
            self.found += [v for k, v in attrs if k in ("src", "href") and v]


def assets_of(html: str) -> list[str]:
    parser = _Assets()
    parser.feed(html)
    return parser.found


@pytest.mark.parametrize(
    "path", ["/models", "/acme/tiny", f"/acme/tiny/tree/{C1}", "/account/tokens"]
)
def test_a_page_with_its_style_and_script_weighs_under_300_kb_and_loads_nothing_from_outside(
    big, path
):
    page = big.get(path)
    assert page.status_code == 200
    weight = len(page.content)
    for asset in assets_of(page.text):
        assert not re.match(r"(?:[a-z]+:)?//", asset), f"{path} loads {asset} from outside"
        if asset.startswith("/static/"):
            weight += len(big.get(asset).content)
    assert weight < 300 * 1024, weight


# --- NFR2.4: sign-in on the portal's side --------------------------------------------------------
def test_the_sign_in_redirect_and_callback_each_take_under_500_ms_on_the_portal_side(
    portal, keycloak
):
    login_times, callback_times = [], []
    for _ in range(20):
        began = time.perf_counter()
        r = portal.get("/auth/login")
        login_times.append(time.perf_counter() - began)
        back = keycloak.authorize(r.headers["location"], username="ada")
        began = time.perf_counter()
        done = portal.get(back.removeprefix(BASE))
        callback_times.append(time.perf_counter() - began)
        assert done.status_code in (302, 303)
        portal.cookies.clear()
    assert p95(login_times) < 0.5 and p95(callback_times) < 0.5


# --- NFR7.1: 20 at once ------------------------------------------------------------------------------
def test_twenty_people_at_once_keep_the_targets(big):
    paths = [*LISTS, "/acme/tiny"]

    def one(i: int) -> float:
        began = time.perf_counter()
        assert big.get(paths[i % len(paths)]).status_code == 200
        return time.perf_counter() - began

    with ThreadPoolExecutor(max_workers=20) as pool:
        times = list(pool.map(one, range(100)))
    assert sum(t < 1.0 for t in times) >= 95


# --- NFR8.1: nothing but the Catalog, the service and Keycloak ------------------------------------
def test_with_other_sockets_blocked_a_signed_in_visit_still_works(
    catalog_http, keycloak, portal, monkeypatch
):
    put(catalog_http, keycloak.issuer, "acme/tiny", C1)
    refused = []
    real = socket.socket.connect

    def guarded(self, address):
        host = address[0] if isinstance(address, tuple) else None
        if host is not None and not ipaddress.ip_address(socket.gethostbyname(host)).is_loopback:
            refused.append(address)
            raise OSError(f"blocked: {address}")
        return real(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    sign_in(portal, keycloak)
    assert portal.get("/models").status_code == 200
    assert portal.get("/acme/tiny").status_code == 200
    assert refused == []


_ = PNG
