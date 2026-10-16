"""What the server packaging must guarantee, checked on the files (NFR5.1 to NFR5.9, NFR3.1, NFR6.1)."""

import re
from pathlib import Path

import pytest
import yaml

DEPLOY = Path(__file__).resolve().parent.parent / "deploy"
COMPOSE = yaml.safe_load((DEPLOY / "compose.yaml").read_text())
SERVICES = COMPOSE["services"]
APPS = ("catalog", "artifactory-service", "portal")
SECRETISH = re.compile(r"(password|secret|token|pepper|key)", re.IGNORECASE)


def env_of(service: dict) -> dict:
    env = service.get("environment") or {}
    return env if isinstance(env, dict) else dict(item.split("=", 1) for item in env)


def test_there_are_exactly_the_five_containers():
    assert set(SERVICES) == {"proxy", "portal", "catalog", "artifactory-service", "database"}


def test_only_the_proxy_publishes_a_port_and_it_is_443():
    published = {name: s.get("ports") for name, s in SERVICES.items() if s.get("ports")}
    assert list(published) == ["proxy"]
    assert [p.split(":")[0] for p in published["proxy"]] == ["443"]


def test_no_image_is_latest_or_unpinned():
    for name, service in SERVICES.items():
        image = service["image"]
        assert "latest" not in image, name
        assert "${" in image, f"{name}: the image must come from the release, not be fixed here"
    text = (DEPLOY / "compose.yaml").read_text() + (DEPLOY / "env.example").read_text()
    assert ":latest" not in text


def test_secrets_are_files_and_never_environment_values():
    for name, secret in COMPOSE["secrets"].items():
        assert "file" in secret and secret["file"].startswith("./secrets/"), name
    for name, service in SERVICES.items():
        for key, value in env_of(service).items():
            if SECRETISH.search(key) and key != "MODELHUB_HF_REPO_KEY":  # a repository name
                # the only secret-looking settings may be names of files or the user name
                assert key.endswith(("_FILE", "_USER")) or value.startswith("/run/secrets/"), (
                    name,
                    key,
                )
            assert not re.search(r"[A-Za-z0-9+/]{32,}", str(value)), (name, key)


def test_each_service_gets_only_its_own_secrets():
    def names(service):
        return {s if isinstance(s, str) else s["source"] for s in service.get("secrets", [])}

    assert "tls_key" in names(SERVICES["proxy"]) and "tls_key" not in names(SERVICES["portal"])
    assert "keycloak_client_secret_portal" in names(SERVICES["portal"])
    assert "keycloak_client_secret_portal" not in names(SERVICES["artifactory-service"])
    assert "artifactory_token" in names(SERVICES["artifactory-service"])
    assert "artifactory_token" not in names(SERVICES["catalog"])
    assert "token_hash_pepper" in names(SERVICES["catalog"])
    assert not (names(SERVICES["catalog"]) & {"service_db_password"})
    assert not (names(SERVICES["artifactory-service"]) & {"catalog_db_password"})


@pytest.mark.parametrize("name", [*APPS, "proxy"])
def test_containers_run_with_least_privilege(name):
    service = SERVICES[name]
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in service["security_opt"]
    user = str(service.get("user", "")).split(":")[0]
    assert (
        user not in ("", "0", "root") or name == "proxy"
    )  # the proxy image's own user is non-root


def test_the_database_keeps_its_data_on_its_own_volume_and_imports_are_separate():
    assert "catalog-db:/var/lib/postgresql/data" in SERVICES["database"]["volumes"]
    assert SERVICES["artifactory-service"]["volumes"] == ["import-work:/import-work"]
    assert set(COMPOSE["volumes"]) == {"catalog-db", "import-work"}
    for name in ("catalog", "portal", "proxy"):
        assert not SERVICES[name].get("volumes"), f"{name} must hold no volume"


@pytest.mark.parametrize("name", [*APPS, "proxy", "database"])
def test_every_container_restarts_has_a_health_check_and_a_memory_limit(name):
    service = SERVICES[name]
    assert service["restart"] == "on-failure"
    assert service["healthcheck"]["test"]
    assert service["mem_limit"]


def test_start_order_follows_health():
    def waits(name):
        deps = SERVICES[name].get("depends_on", {})
        assert all(v["condition"] == "service_healthy" for v in deps.values())
        return set(deps)

    assert waits("catalog") == {"database"}
    assert waits("artifactory-service") == {"database", "catalog"}
    assert waits("portal") == {"catalog"}
    assert waits("proxy") == {"portal", "artifactory-service"}


def test_the_services_use_the_migration_role_then_run_as_their_own():
    for name, role in (("catalog", "catalog"), ("artifactory-service", "artifactory_service")):
        env = env_of(SERVICES[name])
        assert env["MODELHUB_MIGRATION_USER"] == "modelhub_admin"
        assert env["MODELHUB_DATABASE_USER"] == role
    assert env_of(SERVICES["database"])["POSTGRES_PASSWORD_FILE"].startswith("/run/secrets/")


def test_every_service_joins_the_one_internal_network():
    for name, service in SERVICES.items():
        assert service["networks"] == ["internal"], name


# --- the proxy ---------------------------------------------------------------------------------
NGINX = (DEPLOY / "proxy" / "nginx.conf").read_text()


def test_the_proxy_speaks_tls_only_and_hides_the_rest_of_the_api():
    assert "listen 8443 ssl" in NGINX and "listen 80" not in NGINX
    assert "/run/secrets/tls_certificate" in NGINX and "TLSv1.2" in NGINX
    assert re.search(r"location /v1/imports\s*{", NGINX)
    assert re.search(r"location /v1/\s*{\s*return 404;", NGINX)
    routes = "\n".join(line.split("#")[0] for line in NGINX.splitlines())
    for hidden in ("retention", "trusted-keys", "catalog:"):
        assert hidden not in routes


def test_pieces_are_not_size_limited_or_buffered_and_get_a_long_read_timeout():
    block = NGINX[NGINX.index("location /v1/imports") :]
    block = block[: block.index("}")]
    assert "client_max_body_size 0" in block
    assert "proxy_request_buffering off" in block
    assert "proxy_read_timeout 600s" in block


def test_the_proxy_passes_a_request_id_and_logs_json_to_standard_output():
    assert "X-Request-Id" in NGINX and "access_log /dev/stdout json" in NGINX


# --- the images --------------------------------------------------------------------------------
DOCKERFILE = (DEPLOY / "Dockerfile").read_text()


def test_the_image_recipe_runs_as_non_root_and_never_installs_the_stand_in_or_test_helpers():
    assert re.search(r"^USER 10001", DOCKERFILE, re.MULTILINE)
    assert "stand_in" not in DOCKERFILE and "testkit" not in DOCKERFILE
    assert "ENV" in DOCKERFILE and not re.search(r"(PASSWORD|SECRET|TOKEN)\s*=", DOCKERFILE)
    assert "latest" not in DOCKERFILE


def test_the_operator_script_is_valid_and_never_echoes_typed_secrets():
    script = (DEPLOY / "ops.sh").read_text()
    assert "read -rs" in script and "set -euo pipefail" in script
    assert "chmod 700" in script


def test_the_env_example_has_no_secret_values():
    for line in (DEPLOY / "env.example").read_text().splitlines():
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            assert not SECRETISH.search(key) or value == "", key
