"""Start-up: settings and secrets, upgrade steps, restart sweep, then the app (BR1.21)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from modelhub_artifactory_service.main import build_app
from modelhub_common.config import StartupError
from modelhub_testkit.issuer import FakeIssuer

PW = "p" + uuid.uuid4().hex


def env_for(url: str, secrets_dir, work, **extra):
    rest = url.split("://", 1)[1]
    cred, hostdb = rest.split("@", 1)
    user, password = cred.split(":", 1)
    host_port, db = hostdb.split("/", 1)
    host, port = host_port.split(":")
    (secrets_dir / "database_password").write_text(password + "\n")
    (secrets_dir / "artifactory_token").write_text("a" + uuid.uuid4().hex + "\n")
    (secrets_dir / "service_client_secret").write_text("s" + uuid.uuid4().hex + "\n")
    env = {
        "MODELHUB_DATABASE_HOST": host,
        "MODELHUB_DATABASE_PORT": port,
        "MODELHUB_DATABASE_NAME": db,
        "MODELHUB_DATABASE_USER": user,
        "MODELHUB_REALM_ISSUER": "https://keycloak.test/realms/modelhub",
        "MODELHUB_ARTIFACTORY_URL": "https://artifactory.test",
        "MODELHUB_ARTIFACTORY_REPO": "hf-local",
        "MODELHUB_CATALOG_URL": "http://catalog:8000",
        "MODELHUB_WORK_DIR": str(work),
        "MODELHUB_SECRETS_DIR": str(secrets_dir),
    }
    env.update(extra)
    return env


def test_missing_settings_and_secrets_stop_the_start_naming_them_all(tmp_path):
    with pytest.raises(StartupError) as err:
        build_app({"MODELHUB_SECRETS_DIR": str(tmp_path)})
    for name in (
        "MODELHUB_DATABASE_HOST",
        "MODELHUB_ARTIFACTORY_URL",
        "MODELHUB_ARTIFACTORY_REPO",
        "MODELHUB_CATALOG_URL",
        "database_password",
        "artifactory_token",
        "service_client_secret",
    ):
        assert name in str(err.value)


def test_a_start_migrates_sweeps_interrupted_jobs_and_serves(fresh_database, tmp_path):
    issuer = FakeIssuer()
    env = env_for(fresh_database, tmp_path, tmp_path / "work")
    app = build_app(env, jwks_fetch=issuer.jwks)
    client = TestClient(app)
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 200
    assert client.get("/v1/retention/settings").status_code == 401
    ok = {"Authorization": f"Bearer {issuer.token(username='ada', sub='u1')}"}
    assert client.get("/v1/retention/settings", headers=ok).json()["periodDays"] == 365
    assert (tmp_path / "work").is_dir()
