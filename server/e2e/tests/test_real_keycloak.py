"""The sign-in path against a REAL Keycloak (the test-only one in deploy/keycloak/).

Starts the real Keycloak from its compose file, runs the portal, Catalog and import service on
real local ports as the whole-stack test does (with the Artifactory stand-in), and shows: the
portal login in Chrome as the ordinary user and as the administrator, a personal token made in
the portal, and the import service's own client-credentials token accepted by the Catalog.
Requirements FR6.2, NFR3. Skips with a clear message where Docker, Chrome or Playwright is missing,
or where port 8080 is already in use.
"""

import json
import re
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path

import httpx
import pytest
from modelhub_stand_in.server import StandIn
from test_whole_stack import LOCAL, Served, _no_xet, free_port  # noqa: F401 - fixtures

playwright_api = pytest.importorskip("playwright.sync_api", reason="needs: pip install playwright")

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "deploy" / "keycloak" / "compose.keycloak.yaml"
REALM = json.loads(
    (ROOT / "deploy" / "keycloak" / "modelhub-realm.json").read_text(encoding="utf-8")
)
ISSUER = "http://keycloak:8080/realms/modelhub"
SECRETS = {c["clientId"]: c["secret"] for c in REALM["clients"]}
PASSWORDS = {u["username"]: u["credentials"][0]["value"] for u in REALM["users"]}
ADMIN = ("admin", "admin-password-test-not-for-production")
STARTUP_LIMIT_SECONDS = 120  # NFR3


def docker_compose(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), *args],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="module")
def keycloak():
    """The real Keycloak, started once for this module; yields the seconds it took to be ready."""
    if shutil.which("docker") is None or docker_compose("version").returncode != 0:
        pytest.skip("Docker with Compose is not available")
    with socket.socket() as probe:
        if probe.connect_ex((LOCAL, 8080)) == 0:
            pytest.skip("port 8080 is already in use; stop what is using it")
    began = time.monotonic()
    started = docker_compose("up", "-d", "--wait", "--wait-timeout", str(STARTUP_LIMIT_SECONDS))
    took = time.monotonic() - began
    try:
        assert started.returncode == 0, started.stdout + started.stderr
        yield took
    finally:
        docker_compose("down", "-v", "--remove-orphans")


@pytest.fixture
def named_keycloak(keycloak, monkeypatch):
    """Inside this test process the name `keycloak` means this computer, as it does for Chrome."""
    real = socket.getaddrinfo

    def mapped(host, *args, **kwargs):
        return real(LOCAL if host == "keycloak" else host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", mapped)
    return keycloak


def admin_token() -> str:
    r = httpx.post(
        f"http://{LOCAL}:8080/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": ADMIN[0],
            "password": ADMIN[1],
        },
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def allow_redirect(portal_url: str) -> None:
    """The portal runs on a free port: add its address to the portal client's redirect addresses."""
    h = {"Authorization": f"Bearer {admin_token()}"}
    base = f"http://{LOCAL}:8080/admin/realms/modelhub/clients"
    found = httpx.get(base, params={"clientId": "modelhub"}, headers=h, timeout=30).json()[0]
    found["redirectUris"] = [*found["redirectUris"], portal_url + "/auth/callback"]
    done = httpx.put(f"{base}/{found['id']}", json=found, headers=h, timeout=30)
    assert done.status_code == 204, done.text


@pytest.fixture
def real_stack(named_keycloak, fresh_database, tmp_path):
    from modelhub_artifactory_service.main import build_app as build_service
    from modelhub_catalog.main import build_app as build_catalog
    from modelhub_portal.main import build_app as build_portal

    rest = fresh_database.split("://", 1)[1]
    cred, hostdb = rest.split("@", 1)
    user, password = cred.split(":", 1)
    host_port, db = hostdb.split("/", 1)
    host, port = host_port.split(":")

    def secrets(name: str, **files) -> str:
        folder = tmp_path / name
        folder.mkdir()
        for key, value in files.items():
            (folder / key).write_text(value + "\n")
        return str(folder)

    artifactory_token = "a" + uuid.uuid4().hex
    database = {
        "MODELHUB_DATABASE_HOST": host,
        "MODELHUB_DATABASE_PORT": port,
        "MODELHUB_DATABASE_NAME": db,
        "MODELHUB_DATABASE_USER": user,
    }
    ports = {n: free_port() for n in ("catalog", "service", "portal")}
    portal_url = f"http://{LOCAL}:{ports['portal']}"
    allow_redirect(portal_url)
    common = {"MODELHUB_REALM_ISSUER": ISSUER}
    with StandIn(token=artifactory_token, repo_key="hf-local", workdir=tmp_path / "art") as art:
        catalog_app = build_catalog(
            {
                **common,
                **database,
                "MODELHUB_SECRETS_DIR": secrets(
                    "catalog", database_password=password, token_hash_pepper="x" + uuid.uuid4().hex
                ),
            }
        )
        with Served(catalog_app, ports["catalog"]) as catalog:
            service_app = build_service(
                {
                    **common,
                    **database,
                    "MODELHUB_CATALOG_URL": catalog.url,
                    "MODELHUB_ARTIFACTORY_URL": art.url,
                    "MODELHUB_ARTIFACTORY_REPO": "hf-local",
                    "MODELHUB_WORK_DIR": str(tmp_path / "work"),
                    "MODELHUB_UPLOAD_TOOL": "huggingface_hub",
                    "MODELHUB_SECRETS_DIR": secrets(
                        "service",
                        database_password=password,
                        artifactory_token=artifactory_token,
                        service_client_secret=SECRETS["modelhub-artifactory-service"],
                    ),
                }
            )
            portal_app = build_portal(
                {
                    **common,
                    "MODELHUB_PUBLIC_URL": portal_url,
                    "MODELHUB_CATALOG_URL": catalog.url,
                    "MODELHUB_SERVICE_URL": f"http://{LOCAL}:{ports['service']}",
                    "MODELHUB_ARTIFACTORY_URL": art.url,
                    "MODELHUB_HF_REPO_KEY": "hf-local",
                    "MODELHUB_SECRETS_DIR": secrets(
                        "portal", keycloak_client_secret=SECRETS["modelhub"]
                    ),
                }
            )
            with (
                Served(service_app, ports["service"]) as service,
                Served(portal_app, ports["portal"]) as portal,
            ):
                yield {"catalog": catalog, "service": service, "portal": portal}


@pytest.fixture
def chrome():
    with playwright_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                channel="chrome",
                headless=True,
                args=[f"--host-resolver-rules=MAP keycloak {LOCAL}"],
            )
        except playwright_api.Error as exc:
            pytest.skip(f"Google Chrome is not installed: {str(exc).splitlines()[0]}")
        try:
            yield browser
        finally:
            browser.close()


def sign_in(chrome, portal_url: str, username: str):
    """A new private browser window signs in to the portal through Keycloak's own login page."""
    page = chrome.new_context().new_page()
    page.goto(portal_url + "/models")
    page.wait_for_selector("#username")  # Keycloak's login page
    assert page.url.startswith("http://keycloak:8080/realms/modelhub/")
    page.fill("#username", username)
    page.fill("#password", PASSWORDS[username])
    page.click("#kc-login")
    page.wait_for_url(re.compile(re.escape(portal_url) + r"/models.*"))
    return page


# --- the realm is ready in time (NFR3) ---------------------------------------------------------------
def test_keycloak_is_ready_within_two_minutes(keycloak):
    assert keycloak < STARTUP_LIMIT_SECONDS


# --- the portal login in Chrome (FR6.2) ----------------------------------------------------------------
def test_an_ordinary_person_signs_in_to_the_portal_and_cannot_open_the_administrator_screens(
    chrome, real_stack
):
    portal = real_stack["portal"].url
    page = sign_in(chrome, portal, "ada")
    assert "ada" in page.inner_text("body")
    denied = page.goto(portal + "/admin/keys")
    assert denied.status == 403


def test_the_administrator_signs_in_and_opens_the_administrator_screens(chrome, real_stack):
    portal = real_stack["portal"].url
    page = sign_in(chrome, portal, "root")
    opened = page.goto(portal + "/admin/keys")
    assert opened.status == 200 and "Trusted keys" in page.inner_text("body")


def test_a_personal_token_is_made_in_the_portal_after_the_real_sign_in(chrome, real_stack):
    portal = real_stack["portal"].url
    page = sign_in(chrome, portal, "ada")
    page.goto(portal + "/account/tokens")
    page.fill("#name", "from the real keycloak")
    page.click("button:has-text('Make token')")
    page.wait_for_selector("#new-token")
    assert page.inner_text("#new-token").startswith("mhi_")


def test_signing_out_ends_the_portal_session(chrome, real_stack):
    portal = real_stack["portal"].url
    page = sign_in(chrome, portal, "ada")
    page.click("button:has-text('Sign out')")
    page.wait_for_load_state()
    page.goto(portal + "/models")
    page.wait_for_selector("#username")  # asked to sign in again


# --- the import service's own token (FR6.2) -------------------------------------------------------------
def test_the_import_services_own_token_is_accepted_by_the_catalog(chrome, real_stack):
    from modelhub_artifactory_service.catalog_client import ServiceTokenProvider

    portal, catalog = real_stack["portal"].url, real_stack["catalog"].url
    page = sign_in(chrome, portal, "ada")
    page.goto(portal + "/account/tokens")
    page.fill("#name", "to check")
    page.click("button:has-text('Make token')")
    page.wait_for_selector("#new-token")
    personal = page.inner_text("#new-token")

    provider = ServiceTokenProvider(
        ISSUER + "/protocol/openid-connect/token",
        "modelhub-artifactory-service",
        lambda: SECRETS["modelhub-artifactory-service"],
    )
    asked = httpx.post(
        catalog + "/v1/tokens/introspect",
        json={"token": personal},
        headers={"Authorization": f"Bearer {provider()}"},
        timeout=30,
    )
    assert asked.status_code == 200, asked.text
    assert asked.json()["active"] is True


def test_the_catalog_refuses_a_person_on_the_service_only_route(chrome, real_stack):
    """A person's token from the same Keycloak is not the service's identity."""
    catalog = real_stack["catalog"].url
    token = httpx.post(
        ISSUER + "/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "modelhub",
            "client_secret": SECRETS["modelhub"],
        },
        timeout=30,
    )
    # the portal client has no service account: Keycloak refuses to give it a service token
    assert token.status_code in (400, 401)
    refused = httpx.post(catalog + "/v1/tokens/introspect", json={"token": "mhi_x"}, timeout=30)
    assert refused.status_code == 401


# --- no outside connection (NFR4) -----------------------------------------------------------------------
def test_keycloak_starts_and_serves_its_realm_on_a_network_with_no_route_out(tmp_path):
    """On a network with no route to the internet the container still becomes healthy: its health
    check (inside the container) needs the realm's discovery address to answer."""
    if shutil.which("docker") is None or docker_compose("version").returncode != 0:
        pytest.skip("Docker with Compose is not available")
    override = tmp_path / "no-route.yaml"
    override.write_text(
        "services:\n  keycloak:\n    ports: !reset []\n"
        "networks:\n  internal:\n    name: modelhub-no-route\n    internal: true\n",
        encoding="utf-8",
    )
    base = ["docker", "compose", "-p", "kc-no-route", "-f", str(COMPOSE), "-f", str(override)]
    try:
        up = subprocess.run(
            [*base, "up", "-d", "--wait", "--wait-timeout", str(STARTUP_LIMIT_SECONDS)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert up.returncode == 0, up.stdout + up.stderr
        reach = subprocess.run(
            [*base, "exec", "-T", "keycloak", "bash", "-c", "exec 3<>/dev/tcp/1.1.1.1/443"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        assert reach.returncode != 0  # and really no way out, so the health above proves it
    finally:
        subprocess.run([*base, "down", "-v", "--remove-orphans"], capture_output=True, check=False)
