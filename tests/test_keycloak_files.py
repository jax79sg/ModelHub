"""The test-only Keycloak for ModelHub: realm file, container, wiring, guide, kept out of the pack.

Everything here is checked on the files (no Docker needed); the real sign-in tests are in
`server/e2e/tests/test_real_keycloak.py`. Requirements FR1 to FR6, NFR1, NFR2, NFR4, NFR5.
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
KC = ROOT / "deploy" / "keycloak"
REALM = json.loads((KC / "modelhub-realm.json").read_text(encoding="utf-8"))


def client(client_id: str) -> dict:
    return next(c for c in REALM["clients"] if c["clientId"] == client_id)


def audience_mapped(c: dict) -> bool:
    return any(
        m["protocolMapper"] == "oidc-audience-mapper"
        and m["config"].get("included.client.audience") == "modelhub"
        and m["config"].get("access.token.claim") == "true"
        for m in c.get("protocolMappers", [])
    )


# --- RealmDefinition (FR2, FR3, FR4, FR6.1, NFR5) --------------------------------------------------
def test_the_realm_is_named_modelhub_and_enabled():
    assert REALM["realm"] == "modelhub" and REALM["enabled"] is True


def test_the_administrator_role_exists():
    assert "modelhub-admin" in {r["name"] for r in REALM["roles"]["realm"]}


def test_the_portal_client_is_confidential_code_flow_with_a_proof_key():
    portal = client("modelhub")
    assert portal["publicClient"] is False and portal["standardFlowEnabled"] is True
    assert (
        portal["serviceAccountsEnabled"] is False and portal["directAccessGrantsEnabled"] is False
    )
    assert portal["attributes"]["pkce.code.challenge.method"] == "S256"
    assert portal["redirectUris"] and all(
        u.endswith("/auth/callback") for u in portal["redirectUris"]
    )
    assert portal["attributes"]["post.logout.redirect.uris"]
    assert "secret" in portal


def test_the_portal_client_puts_the_audience_modelhub_in_its_tokens():
    assert audience_mapped(client("modelhub"))


def test_the_service_client_is_client_credentials_only_with_the_audience():
    service = client("modelhub-artifactory-service")
    assert service["publicClient"] is False and service["serviceAccountsEnabled"] is True
    assert service["standardFlowEnabled"] is False and service["directAccessGrantsEnabled"] is False
    assert audience_mapped(service) and "secret" in service


def test_there_is_one_ordinary_and_one_administrator_test_user():
    users = {u["username"]: u for u in REALM["users"] if not u["username"].startswith("service-")}
    assert set(users) == {"ada", "root"}
    assert users["ada"].get("realmRoles", []) == []
    assert users["root"]["realmRoles"] == ["modelhub-admin"]
    for u in users.values():
        assert (
            u["enabled"] and u["emailVerified"] and u["firstName"] and u["lastName"] and u["email"]
        )
        assert u["credentials"][0]["temporary"] is False


def test_every_secret_and_password_is_plainly_marked_as_a_test_value():
    values = [c["secret"] for c in REALM["clients"] if "secret" in c]
    values += [cred["value"] for u in REALM["users"] for cred in u.get("credentials", [])]
    assert len(values) == 4
    for value in values:
        assert "test" in value and "not-for-production" in value, value


def test_the_realm_file_says_in_words_that_it_is_for_testing_only():
    assert "test only" in REALM["displayName"].lower()
    assert "never" in REALM["attributes"]["note"].lower()  # Keycloak has no realm description field


# --- KeycloakContainer (FR1, NFR2, NFR4) ---------------------------------------------------------------
IMAGE = "quay.io/keycloak/keycloak:26.8.1"


def compose() -> dict:
    return yaml.safe_load((KC / "compose.keycloak.yaml").read_text(encoding="utf-8"))


def keycloak_service() -> dict:
    return compose()["services"]["keycloak"]


def test_the_image_is_pinned_to_an_exact_version_and_never_latest():
    assert keycloak_service()["image"] == IMAGE
    assert "latest" not in (KC / "compose.keycloak.yaml").read_text(encoding="utf-8")


def test_only_port_8080_on_the_local_machine_is_published():
    assert keycloak_service()["ports"] == ["127.0.0.1:8080:8080"]


def test_it_starts_in_development_mode_and_imports_the_realm_file():
    service = keycloak_service()
    assert service["command"][0] == "start-dev" and "--import-realm" in service["command"]
    mounts = [v for v in service["volumes"] if "modelhub-realm.json" in v]
    assert mounts and mounts[0].endswith(":/opt/keycloak/data/import/modelhub-realm.json:ro")


def test_its_address_is_its_own_name_so_the_issuer_is_the_same_everywhere():
    env = keycloak_service()["environment"]
    assert env["KC_HOSTNAME"] == "http://keycloak:8080"
    assert env["KC_HOSTNAME_BACKCHANNEL_DYNAMIC"] == "false"
    assert env["KC_HEALTH_ENABLED"] == "true"


def test_the_container_is_named_keycloak_on_the_stacks_network_and_has_a_health_check():
    spec = compose()
    assert "keycloak" in spec["services"] and keycloak_service()["healthcheck"]["test"]
    assert "realms/modelhub" in " ".join(keycloak_service()["healthcheck"]["test"])
    assert spec["networks"]["internal"]["name"] == "modelhub-internal"


def test_the_admin_account_of_the_test_keycloak_is_marked_as_a_test_value():
    env = keycloak_service()["environment"]
    assert "test-not-for-production" in env["KC_BOOTSTRAP_ADMIN_PASSWORD"]


def test_the_compose_file_is_readable_by_docker_compose():
    import shutil
    import subprocess

    if shutil.which("docker") is None:
        pytest.skip("Docker is not installed")
    done = subprocess.run(
        ["docker", "compose", "-f", str(KC / "compose.keycloak.yaml"), "config", "--quiet"],
        capture_output=True,
        text=True,
        check=False,
    )
    if "unknown shorthand flag" in done.stderr or "is not a docker command" in done.stderr:
        pytest.skip("the Docker Compose plugin is not installed")
    assert done.returncode == 0, done.stderr


# --- TestStackWiring (FR5, NFR1) ------------------------------------------------------------------------
STACK = KC / "compose.stack.yaml"
UP = KC / "up.sh"
GUIDE = KC / "README.md"


def test_the_stand_in_file_can_run_the_artifactory_stand_in_alone():
    text = (ROOT / "deploy" / "smoke" / "standins.py").read_text(encoding="utf-8")
    assert "SIGNIN_STANDIN" in text and "environ" in text


def test_the_stack_file_runs_only_the_artifactory_stand_in_and_waits_for_keycloak():
    spec = yaml.safe_load(STACK.read_text(encoding="utf-8").replace("!override", ""))["services"]
    assert spec["standins"]["environment"]["SIGNIN_STANDIN"] == "0"
    for name in ("catalog", "artifactory-service", "portal"):
        assert spec[name]["depends_on"]["keycloak"]["condition"] == "service_healthy"


def test_the_stack_file_publishes_the_proxy_only_on_the_local_machine_at_8443():
    text = STACK.read_text(encoding="utf-8")
    assert "!override" in text and "127.0.0.1:8443:8443" in text


def test_the_start_script_is_valid_shell_and_fills_the_stack_from_the_realm_file():
    import subprocess

    text = UP.read_text(encoding="utf-8")
    if (
        sys.platform != "win32"
    ):  # the script is for Linux and macOS; Windows may check it out with CRLF
        assert subprocess.run(["bash", "-n", str(UP)], check=False).returncode == 0
    assert "KEYCLOAK_ISSUER=http://keycloak:8080/realms/modelhub" in text
    assert "modelhub-realm.json" in text and "init-secrets" in text
    assert "'modelhub'" in text and "'modelhub-artifactory-service'" in text
    assert "compose.keycloak.yaml" in text and "compose.stack.yaml" in text


def test_the_start_script_never_prints_a_secret():
    text = UP.read_text(encoding="utf-8")
    for secret in [c["secret"] for c in REALM["clients"] if "secret" in c]:
        assert secret not in text


def test_the_guide_lists_every_realm_role_client_user_and_claim_to_set_up():
    guide = GUIDE.read_text(encoding="utf-8")
    needed = [REALM["realm"], "modelhub-admin", "http://keycloak:8080/realms/modelhub"]
    needed += [c["clientId"] for c in REALM["clients"]]
    needed += [u["username"] for u in REALM["users"]]
    needed += [
        "aud",
        "azp",
        "sub",
        "preferred_username",
        "realm_access",
        "S256",
        "client credentials",
    ]
    needed += [uri for c in REALM["clients"] for uri in c.get("redirectUris", [])]
    assert [item for item in needed if item not in guide] == []
    assert "never" in guide.lower() and "test only" in guide.lower()


# --- Kept out of the pack (NFR1) --------------------------------------------------------------------------
def test_the_pack_build_copies_nothing_from_the_keycloak_folder():
    script = (ROOT / "deploy" / "build-pack.sh").read_text(encoding="utf-8")
    assert "keycloak" not in script.lower()


def test_the_whole_test_stack_is_readable_by_docker_compose_with_the_start_script_settings():
    import os
    import shutil
    import subprocess

    if shutil.which("docker") is None:
        pytest.skip("Docker is not installed")
    deploy = ROOT / "deploy"
    env = {
        **os.environ,
        "MODELHUB_VERSION": "t",
        "SMOKE_VERSION": "t",
        "POSTGRES_IMAGE": "postgres:16",
        "KEYCLOAK_ISSUER": "http://keycloak:8080/realms/modelhub",
        "PUBLIC_URL": "https://modelhub.test:8443",
        "ARTIFACTORY_URL": "http://standins:9100",
        "ARTIFACTORY_REPO": "hf-local",
    }
    done = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "compose.yaml",
            "-f",
            "keycloak/compose.keycloak.yaml",
            "-f",
            "keycloak/compose.stack.yaml",
            "config",
            "--format",
            "json",
        ],
        cwd=deploy,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if "unknown shorthand flag" in done.stderr or "is not a docker command" in done.stderr:
        pytest.skip("the Docker Compose plugin is not installed")
    assert done.returncode == 0, done.stderr
    services = json.loads(done.stdout)["services"]
    assert {"keycloak", "standins", "catalog", "portal", "artifactory-service", "proxy"} <= set(
        services
    )
    assert services["proxy"]["ports"] == [
        {
            "mode": "ingress",
            "host_ip": "127.0.0.1",
            "target": 8443,
            "published": "8443",
            "protocol": "tcp",
        }
    ]


# --- CI (FR6.3) -----------------------------------------------------------------------------------------
def test_ci_runs_the_real_keycloak_sign_in_tests_and_fails_where_chrome_or_docker_is_missing():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    job = ci[ci.index("keycloak-real:") :]
    job = job[: job.index("\n  # ")] if "\n  # " in job else job
    assert "name: keycloak (real sign-in)" in job
    assert "google-chrome --version" in job and "docker compose version" in job
    assert "server/e2e/tests/test_real_keycloak.py" in job and "-rs" in job
    assert "postgres:16" in job and "playwright" in job
    assert "skipped" in job  # the run fails if the tests were skipped instead of run


def test_the_stand_in_file_really_runs_only_the_artifactory_stand_in_when_told_to(tmp_path):
    import os
    import subprocess
    import sys

    pytest.importorskip("modelhub_stand_in")
    token = tmp_path / "token"
    token.write_text("test-token-not-for-production\n", encoding="utf-8")
    env = {**os.environ, "SIGNIN_STANDIN": "0", "ARTIFACTORY_TOKEN_FILE": str(token)}
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "deploy" / "smoke" / "standins.py")],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        line = proc.stdout.readline()
    finally:
        proc.kill()
        proc.communicate()
    assert line.startswith("no sign-in stand-in; Artifactory stand-in at ")
