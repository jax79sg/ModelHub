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
    assert waits("portal") == {"catalog", "artifactory-service"}
    assert waits("proxy") == {"portal", "artifactory-service"}


def test_the_services_use_the_migration_role_then_run_as_their_own():
    for name, role in (("catalog", "catalog"), ("artifactory-service", "artifactory_service")):
        env = env_of(SERVICES[name])
        assert env["MODELHUB_MIGRATION_USER"] == "modelhub_admin"
        assert env["MODELHUB_DATABASE_USER"] == role
    assert env_of(SERVICES["database"])["POSTGRES_PASSWORD_FILE"].startswith("/run/secrets/")


def test_every_service_joins_the_one_internal_network():
    for name, service in SERVICES.items():
        assert list(service["networks"]) == ["internal"], name


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


def test_the_image_uses_ordinary_large_file_uploads_and_sends_no_telemetry():
    # Artifactory takes Git LFS uploads; the newer Xet transfer is not assumed (contract C5).
    assert "HF_HUB_DISABLE_XET=1" in DOCKERFILE and "HF_HUB_DISABLE_TELEMETRY=1" in DOCKERFILE


# --- the JFrog CLI in the import service image only (NFR10.1, NFR8.1) -------------------------
def test_the_import_service_image_carries_a_pinned_checked_jfrog_cli():
    assert re.search(r"^ARG JF_VERSION=\d+\.\d+\.\d+$", DOCKERFILE, re.MULTILINE)
    for arch in ("AMD64", "ARM64"):
        assert re.search(rf"^ARG JF_SHA256_{arch}=[0-9a-f]{{64}}$", DOCKERFILE, re.MULTILINE), arch
    assert "sha256sum -c" in DOCKERFILE
    assert "releases.jfrog.io/artifactory/jfrog-cli/v2-jf/${JF_VERSION}" in DOCKERFILE


def test_the_jfrog_cli_is_installed_for_the_import_service_unit_and_no_other():
    block = DOCKERFILE[DOCKERFILE.index("JF_VERSION") :]
    assert '"${UNIT}" = "artifactory_service"' in block
    for other in ("catalog", "portal"):
        assert f'"${{UNIT}}" = "{other}"' not in block


def test_the_jfrog_cli_does_not_check_for_updates_or_report_usage():
    assert "JFROG_CLI_AVOID_NEW_VERSION_WARNING=true" in DOCKERFILE
    assert "JFROG_CLI_REPORT_USAGE=false" in DOCKERFILE
    assert "JFROG_CLI_HOME_DIR=/tmp/.jfrog" in DOCKERFILE  # the root file system is read-only


def test_the_ci_image_job_proves_the_cli_is_there_and_only_there():
    ci = (DEPLOY.parent / ".github" / "workflows" / "ci.yml").read_text()
    assert "jf --version" in ci
    assert (
        "modelhub/artifactory-service"
        in ci[ci.index("jf --version") - 400 : ci.index("jf --version") + 400]
    )


# --- the disk minimums are enforced at install (catalog NFR7.2, import service NFR7.6) ------------
def _preflight(tmp_path, free_gb: int, **env):
    import shutil
    import subprocess
    import sys

    if sys.platform == "win32":
        pytest.skip("the operator script is for the Linux server")
    stub = tmp_path / "bin"
    stub.mkdir()
    (stub / "docker").write_text(
        "#!/bin/sh\n"
        'case "$1 $2" in\n'
        '  "info --format") echo /var/lib/docker ;;\n'
        "  *) exit 0 ;;\n"
        "esac\n"
    )
    (stub / "df").write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        '  *-Pk*) echo "Filesystem 1024-blocks Used Available Capacity Mounted"; '
        f'echo "fs 9999999999 1 {free_gb * 1024 * 1024} 1% /" ;;\n'
        '  *) echo "Filesystem Size Used Avail Use% Mounted"; echo "fs 9T 1G 9T 1% /" ;;\n'
        "esac\n"
    )
    for name in ("docker", "df"):
        (stub / name).chmod(0o755)
    home = tmp_path / "deploy"
    home.mkdir()
    for name in ("ops.sh", "compose.yaml"):
        shutil.copy(DEPLOY / name, home / name)
    (home / ".env").write_text(
        "PUBLIC_URL=https://modelhub.example.org\nKEYCLOAK_ISSUER=https://kc/realms/x\n"
        "ARTIFACTORY_URL=https://art\nARTIFACTORY_REPO=hf-local\n"
    )
    return subprocess.run(
        ["bash", str(home / "ops.sh"), "preflight"],
        env={"PATH": f"{stub}:/usr/bin:/bin", "HOME": str(tmp_path), **env},
        capture_output=True,
        text=True,
        check=False,
    )


def test_preflight_refuses_a_server_with_less_than_540_gb_free(tmp_path):
    done = _preflight(tmp_path, free_gb=300)
    assert done.returncode == 1
    assert "Problem" in done.stderr and "540 GB" in done.stderr


def test_preflight_accepts_a_server_with_enough_space(tmp_path):
    done = _preflight(tmp_path, free_gb=600)
    assert done.returncode == 0, done.stderr


def test_preflight_can_be_told_a_small_test_server_is_fine(tmp_path):
    done = _preflight(tmp_path, free_gb=100, MODELHUB_PREFLIGHT_SMALL="1")
    assert done.returncode == 0, done.stderr
    assert "small" in done.stdout.lower()


# --- the stack needs no route to the internet (platform NFR8.1) ----------------------------------
def test_the_smoke_test_runs_the_whole_stack_on_a_network_with_no_route_out():
    smoke = (DEPLOY / "smoke" / "compose.smoke.yaml").read_text()
    assert re.search(r"^networks:\n  internal:\n    internal: true", smoke, re.MULTILINE)
    assert "ports: !reset []" in smoke  # nothing can be published from a network with no route


def test_the_smoke_test_checks_that_a_product_container_cannot_reach_the_internet():
    script = (DEPLOY / "smoke" / "run.sh").read_text()
    assert "cannot reach the internet" in script
    assert "the check below would prove nothing" in script  # a control comes before each test
    for name in ("catalog", "portal", "artifactory-service", "proxy"):
        assert name in script[script.index("no route out") :]
    assert script.index("no route out") < script.index("release $FROM: start, first import") or (
        script.index("no route out") > script.index('drive "$FROM" import')
    )
    assert script.index("no route out") < script.index("smoke test and rehearsal passed")
