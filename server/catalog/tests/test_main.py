"""Start-up: settings and secrets, upgrade steps, then the app (rules BR1.6, BR1.7, BR1.21)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from modelhub_catalog.main import build_app, database_url
from modelhub_common.config import StartupError
from modelhub_testkit.issuer import FakeIssuer


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
        Secret("database_password", "p@ss/word"),
    )
    assert url == "postgresql://u:p%40ss%2Fword@db:5432/catalog"


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
    (tmp_path / "database_password").write_text("a-database-password-value\n")
    with pytest.raises(StartupError) as err:
        build_app({"MODELHUB_SECRETS_DIR": str(tmp_path)})
    assert "a-database-password-value" not in str(err.value)
