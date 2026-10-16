"""Start-up: settings and secrets, upgrade steps, then the app (rules BR1.6, BR1.7, BR1.21)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from modelhub_catalog.main import build_app, database_url
from modelhub_common.config import StartupError
from modelhub_testkit.issuer import FakeIssuer

LEAK = "v" + uuid.uuid4().hex
PW_RAW = "x@" + uuid.uuid4().hex[:6] + "/y"
PW_ENCODED = PW_RAW.replace("@", "%40").replace("/", "%2F")


def env_for(url: str, secrets_dir, **extra):
    rest = url.split("://", 1)[1]
    cred, hostdb = rest.split("@", 1)
    user, password = cred.split(":", 1)
    host_port, db = hostdb.split("/", 1)
    host, port = host_port.split(":")
    (secrets_dir / "database_password").write_text(password + "\n")
    (secrets_dir / "token_hash_pepper").write_text("pepper-" + uuid.uuid4().hex + "\n")
    env = {
        "MODELHUB_DATABASE_HOST": host,
        "MODELHUB_DATABASE_PORT": port,
        "MODELHUB_DATABASE_NAME": db,
        "MODELHUB_DATABASE_USER": user,
        "MODELHUB_REALM_ISSUER": "https://keycloak.test/realms/modelhub",
        "MODELHUB_SECRETS_DIR": str(secrets_dir),
    }
    env.update(extra)
    return env


def test_a_missing_setting_and_secret_stop_the_start_naming_them_all(tmp_path):
    with pytest.raises(StartupError) as err:
        build_app({"MODELHUB_SECRETS_DIR": str(tmp_path)})
    text = str(err.value)
    for name in (
        "MODELHUB_DATABASE_HOST",
        "MODELHUB_DATABASE_NAME",
        "MODELHUB_REALM_ISSUER",
        "database_password",
        "token_hash_pepper",
    ):
        assert name in text


def test_the_database_url_is_built_from_settings_and_the_password_secret(tmp_path):
    from modelhub_common.secrets import Secret

    url = database_url(
        {
            "MODELHUB_DATABASE_HOST": "db",
            "MODELHUB_DATABASE_PORT": 5432,
            "MODELHUB_DATABASE_NAME": "catalog",
            "MODELHUB_DATABASE_USER": "u",
        },
        Secret("database_password", PW_RAW),
    )
    assert url == "postgresql://u:" + PW_ENCODED + "@db:5432/catalog"


def test_a_good_start_applies_the_upgrade_steps_and_serves_requests(fresh_database, tmp_path):
    issuer = FakeIssuer()
    env = env_for(fresh_database, tmp_path)
    app = build_app(env, jwks_fetch=issuer.jwks)
    client = TestClient(app)
    assert client.get("/readyz").status_code == 200
    token = issuer.token()
    r = client.get("/v1/models", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json()["total"] == 0
    # steps are recorded, so a second start changes nothing
    build_app(env, jwks_fetch=issuer.jwks)


def test_a_database_newer_than_the_code_stops_the_start(fresh_database, tmp_path):
    import psycopg
    from modelhub_catalog.db import DatabaseTooNew, migrate

    migrate(fresh_database)
    with psycopg.connect(fresh_database) as conn:
        conn.execute("insert into schema_steps(step, applied_at) values (9999, now())")
        conn.commit()
    with pytest.raises(DatabaseTooNew):
        build_app(env_for(fresh_database, tmp_path), jwks_fetch=FakeIssuer().jwks)


def test_secrets_never_appear_in_the_start_up_error(tmp_path):
    (tmp_path / "database_password").write_text(LEAK + "\n")
    with pytest.raises(StartupError) as err:
        build_app({"MODELHUB_SECRETS_DIR": str(tmp_path)})
    assert LEAK not in str(err.value)


def test_with_a_migration_role_the_steps_run_as_it_and_the_service_runs_as_a_limited_one(
    fresh_database, tmp_path
):
    """Rule BR1.21, NFR5.5: the running role cannot create objects; the migration role did."""
    import psycopg

    env = env_for(fresh_database, tmp_path)
    admin_password = (tmp_path / "database_password").read_text().strip()
    admin_user = env["MODELHUB_DATABASE_USER"]
    runtime_password = "r" + uuid.uuid4().hex
    (tmp_path / "database_migration_password").write_text(admin_password + "\n")
    (tmp_path / "database_password").write_text(runtime_password + "\n")
    env.update(
        MODELHUB_MIGRATION_USER=admin_user,
        MODELHUB_DATABASE_USER="catalog_rt",
    )
    issuer = FakeIssuer()
    app = build_app(env, jwks_fetch=issuer.jwks)
    client = TestClient(app)
    assert client.get("/readyz").status_code == 200
    ok = {"Authorization": f"Bearer {issuer.token()}"}
    assert client.get("/v1/models", headers=ok).json()["total"] == 0
    runtime_url = (
        f"postgresql://catalog_rt:{runtime_password}@{env['MODELHUB_DATABASE_HOST']}:"
        f"{env['MODELHUB_DATABASE_PORT']}/{env['MODELHUB_DATABASE_NAME']}"
    )
    with psycopg.connect(runtime_url, autocommit=True) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("create table sneaky (a int)")
        assert conn.execute("select count(*) from models").fetchone()[0] == 0


def test_a_migration_user_without_its_secret_stops_the_start(fresh_database, tmp_path):
    env = env_for(fresh_database, tmp_path, MODELHUB_MIGRATION_USER="admin")
    with pytest.raises(StartupError) as err:
        build_app(env, jwks_fetch=FakeIssuer().jwks)
    assert "database_migration_password" in str(err.value)
