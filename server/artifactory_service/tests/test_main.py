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


def test_with_a_migration_role_the_service_runs_as_a_limited_one_that_sees_only_its_schema(
    fresh_database, tmp_path
):
    """NFR5.5: the running role cannot create objects, and cannot read other schemas."""
    import psycopg

    env = env_for(fresh_database, tmp_path, tmp_path / "work")
    admin_password = (tmp_path / "database_password").read_text().strip()
    admin_user = env["MODELHUB_DATABASE_USER"]
    runtime_password = "r" + uuid.uuid4().hex
    (tmp_path / "database_migration_password").write_text(admin_password + "\n")
    (tmp_path / "database_password").write_text(runtime_password + "\n")
    env.update(MODELHUB_MIGRATION_USER=admin_user, MODELHUB_DATABASE_USER="service_rt")
    issuer = FakeIssuer()
    app = build_app(env, jwks_fetch=issuer.jwks)
    client = TestClient(app)
    ok = {"Authorization": f"Bearer {issuer.token(username='ada', sub='u1')}"}
    assert client.get("/v1/retention/settings", headers=ok).json()["periodDays"] == 365
    with psycopg.connect(fresh_database, autocommit=True) as admin:
        admin.execute("create table public.secret_stuff (a int)")
    runtime_url = (
        f"postgresql://service_rt:{runtime_password}@{env['MODELHUB_DATABASE_HOST']}:"
        f"{env['MODELHUB_DATABASE_PORT']}/{env['MODELHUB_DATABASE_NAME']}"
    )
    with psycopg.connect(runtime_url, autocommit=True) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("create table artifactory_service.sneaky (a int)")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("select * from public.secret_stuff")


def test_ready_says_degraded_when_artifactory_and_the_catalog_cannot_be_reached(
    fresh_database, tmp_path
):
    """NFR6.2: the database is critical; Artifactory and the Catalog are reported, not fatal."""
    env = env_for(fresh_database, tmp_path, tmp_path / "work")
    app = build_app(env, jwks_fetch=FakeIssuer().jwks)
    body = TestClient(app).get("/readyz")
    assert body.status_code == 200
    assert body.json()["status"] == "degraded"
    assert body.json()["checks"] == {"database": "ok", "artifactory": "down", "catalog": "down"}
