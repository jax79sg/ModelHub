"""The whole stack on real local ports: sign-in, token, import by the real command, the portal.

Starts PostgreSQL (the test fixture), a sign-in stand-in, the Artifactory stand-in, and the real
Catalog, import service and portal from their own start-up code. A "browser" signs in through the
sign-in stand-in, makes a personal token on the portal, the real command imports a bundle with
it, and the portal then lists and shows the model. This is the first end-to-end proof.
"""

import json
import re
import socket
import threading
import time
import uuid

import httpx
import pytest
import uvicorn
from modelhub_stand_in.server import StandIn
from modelhub_testkit.bundles import make_bundle
from modelhub_testkit.keycloak import KeycloakServer
from typer.testing import CliRunner

from modelhub import cli, signing

LOCAL = "127.0.0.1"


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind((LOCAL, 0))
        return probe.getsockname()[1]


class Served:
    def __init__(self, app, port: int) -> None:
        self.url = f"http://{LOCAL}:{port}"
        self._server = uvicorn.Server(
            uvicorn.Config(app, host=LOCAL, port=port, log_level="warning", lifespan="off")
        )
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def __enter__(self):
        self._thread.start()
        deadline = time.monotonic() + 20
        while not self._server.started:
            assert time.monotonic() < deadline, "a server did not start"
            time.sleep(0.01)
        return self

    def __exit__(self, *exc):
        self._server.should_exit = True
        self._thread.join(timeout=10)


@pytest.fixture(autouse=True)
def _no_xet(monkeypatch):
    monkeypatch.setenv("HF_HUB_DISABLE_XET", "1")
    monkeypatch.setenv("HF_HUB_DISABLE_TELEMETRY", "1")


@pytest.fixture
def stack(fresh_database, tmp_path):
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
    portal_secret = "p" + uuid.uuid4().hex
    service_secret = "s" + uuid.uuid4().hex
    database = {
        "MODELHUB_DATABASE_HOST": host,
        "MODELHUB_DATABASE_PORT": port,
        "MODELHUB_DATABASE_NAME": db,
        "MODELHUB_DATABASE_USER": user,
    }
    ports = {n: free_port() for n in ("catalog", "service", "portal")}
    with (
        KeycloakServer() as keycloak,
        StandIn(token=artifactory_token, repo_key="hf-local", workdir=tmp_path / "art") as art,
    ):
        issuer = keycloak.realm
        common = {"MODELHUB_REALM_ISSUER": issuer}
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
                        service_client_secret=service_secret,
                    ),
                }
            )
            portal_url = f"http://{LOCAL}:{ports['portal']}"
            portal_app = build_portal(
                {
                    **common,
                    "MODELHUB_PUBLIC_URL": portal_url,
                    "MODELHUB_CATALOG_URL": catalog.url,
                    "MODELHUB_SERVICE_URL": f"http://{LOCAL}:{ports['service']}",
                    "MODELHUB_ARTIFACTORY_URL": art.url,
                    "MODELHUB_HF_REPO_KEY": "hf-local",
                    "MODELHUB_SECRETS_DIR": secrets("portal", keycloak_client_secret=portal_secret),
                }
            )
            with (
                Served(service_app, ports["service"]) as service,
                Served(portal_app, ports["portal"]) as portal,
            ):
                yield {
                    "keycloak": keycloak,
                    "artifactory": art,
                    "catalog": catalog,
                    "service": service,
                    "portal": portal,
                }


def browser_sign_in(portal_url: str, who: str = "ada", admin: bool = False) -> httpx.Client:
    """Sign in the way a browser does: follow each redirect, keeping the cookies."""
    browser = httpx.Client(follow_redirects=False, timeout=30)
    r = browser.get(portal_url + "/auth/login")
    assert r.status_code == 302, r.text
    hop = r.headers["location"] + f"&login_hint={who}" + ("&admin=1" if admin else "")
    for _ in range(5):
        r = browser.get(hop)
        if r.status_code != 302:
            break
        hop = r.headers["location"]
        if hop.startswith("/"):
            hop = portal_url + hop
    assert r.status_code == 200, r.text
    return browser


def test_the_whole_path_from_sign_in_to_a_model_in_the_portal(stack, tmp_path, monkeypatch):
    portal = stack["portal"].url
    service = stack["service"].url
    bundle = make_bundle(tmp_path / "b")
    # an administrator trusts the signing key on the portal's keys screen
    root = browser_sign_in(portal, who="root", admin=True)
    keys_page = root.get(portal + "/admin/keys")
    assert keys_page.status_code == 200
    root_csrf = re.search(r'name="_csrf" value="([^"]+)"', keys_page.text).group(1)
    added = root.post(
        portal + "/admin/keys",
        data={
            "name": "release key",
            "public_key": json.dumps(bundle.public_key),
            "fingerprint": bundle.public_key["fingerprint"],
            "_csrf": root_csrf,
        },
        headers={"Origin": portal},
    )
    assert added.status_code == 303, added.text
    assert "release key" in root.get(portal + "/admin/keys").text
    assert "365 days" in root.get(portal + "/admin/retention").text

    ada = browser_sign_in(portal)
    page = ada.get(portal + "/account/tokens")
    assert page.status_code == 200
    csrf = re.search(r'name="_csrf" value="([^"]+)"', page.text).group(1)
    made = ada.post(
        portal + "/account/tokens",
        data={"name": "laptop", "_csrf": csrf},
        headers={"Origin": portal},
    )
    token = re.search(r'id="new-token">(mhi_[^<]+)<', made.text).group(1)

    # the real command, on an import computer that trusts the key, with that token
    monkeypatch.setenv("MODELHUB_HOME", str(tmp_path / "import-computer"))
    (tmp_path / "cwd").mkdir()
    monkeypatch.chdir(tmp_path / "cwd")  # the command writes its run record where it is started
    signing.trust_key(bundle.public_key, bundle.public_key["fingerprint"])
    env = {"MODELHUB_SERVER": service, "MODELHUB_TOKEN": token}
    result = CliRunner().invoke(cli.app, ["import", str(bundle.directory)], env=env)
    assert result.exit_code == 0, result.output
    assert "IMPORTED" in result.output and token not in result.output

    # Artifactory holds the files; the Catalog and the portal show the model
    art = stack["artifactory"]
    assert art.version_state("org/tiny", bundle.commit) == "complete"
    held = {f.path for f in art.version_files("org/tiny", bundle.commit)}
    assert held == set(bundle.files)
    listing = ada.get(portal + "/models")
    assert listing.status_code == 200 and "org/tiny" in listing.text
    model = ada.get(portal + "/org/tiny")
    assert model.status_code == 200 and "Tiny" in model.text and "model.safetensors" in model.text
    assert "jf hf download org/tiny" in model.text

    # the same bundle again is skipped, nothing more is uploaded
    again = CliRunner().invoke(cli.app, ["import", str(bundle.directory)], env=env)
    assert again.exit_code == 0 and "SKIPPED" in again.output

    # a person who is not signed in sees nothing
    outsider = httpx.get(portal + "/models")
    assert outsider.status_code == 302 and "org/tiny" not in outsider.text
