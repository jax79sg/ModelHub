"""Start-up: settings and the secret file, then a working app (NFR5.11, NFR6.1)."""

import uuid

import pytest
from conftest import BASE
from fastapi.testclient import TestClient
from modelhub_common.config import StartupError
from modelhub_portal.main import build_app
from modelhub_testkit.keycloak import FakeKeycloak

LEAK = "k" + uuid.uuid4().hex


def env_for(secrets_dir, **extra):
    (secrets_dir / "keycloak_client_secret").write_text(LEAK + "\n")
    env = {
        "MODELHUB_REALM_ISSUER": "https://keycloak.test/realms/modelhub",
        "MODELHUB_PUBLIC_URL": BASE,
        "MODELHUB_CATALOG_URL": "http://catalog:8000",
        "MODELHUB_ARTIFACTORY_URL": "https://artifactory.test",
        "MODELHUB_HF_REPO_KEY": "hf-local",
        "MODELHUB_SECRETS_DIR": str(secrets_dir),
    }
    env.update(extra)
    return env


def test_missing_settings_and_the_secret_stop_the_start_naming_them_all(tmp_path):
    with pytest.raises(StartupError) as err:
        build_app({"MODELHUB_SECRETS_DIR": str(tmp_path)})
    text = str(err.value)
    for name in (
        "MODELHUB_REALM_ISSUER",
        "MODELHUB_PUBLIC_URL",
        "MODELHUB_CATALOG_URL",
        "keycloak_client_secret",
    ):
        assert name in text
    assert LEAK not in text


def test_a_start_serves_the_health_paths_and_sends_everything_else_to_sign_in(tmp_path):
    kc = FakeKeycloak()
    app = build_app(env_for(tmp_path), jwks_fetch=kc.issuer.jwks, oidc_transport=kc.transport())
    client = TestClient(app, base_url=BASE, follow_redirects=False)
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz").json()
    assert ready["keycloak"] == "ok"
    assert client.get("/models").status_code == 302
    kc.down = True
    assert client.get("/readyz").json()["status"] in ("ok", "degraded")


def test_the_secret_never_appears_in_the_settings_kept_on_the_app(tmp_path):
    kc = FakeKeycloak()
    app = build_app(env_for(tmp_path), jwks_fetch=kc.issuer.jwks, oidc_transport=kc.transport())
    assert LEAK not in repr(app.state.settings)
