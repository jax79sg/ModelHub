"""Secrets and settings are read once at start-up and a bad one stops the start (BR1.6, BR1.7, BR1.12)."""

import uuid

import pytest
from modelhub_common.config import Setting, StartupError, load_config, load_secrets
from modelhub_common.secrets import Secret

V1 = "v" + uuid.uuid4().hex[:12]
V2 = "v" + uuid.uuid4().hex[:12]


def test_a_secret_never_prints(tmp_path):
    secret = Secret("database_password", V1)
    assert V1 not in str(secret)
    assert V1 not in repr(secret)
    assert V1 not in f"{secret!s} {secret!r} {[secret]} {{'k': secret}}"
    assert secret.reveal() == V1


def test_a_secret_cannot_be_serialised(tmp_path):
    import json

    with pytest.raises(TypeError):
        json.dumps(Secret("x", "v"))


def test_secrets_are_read_from_files_and_one_newline_is_stripped(tmp_path):
    (tmp_path / "database_password").write_text(V1 + "\n")
    (tmp_path / "token_hash_pepper").write_text(V2 + "  \n\n")
    got = load_secrets(["database_password", "token_hash_pepper"], directory=tmp_path)
    assert got["database_password"].reveal() == V1
    assert got["token_hash_pepper"].reveal() == V2 + "  \n"


def test_the_folder_comes_from_the_environment(tmp_path):
    (tmp_path / "artifactory_token").write_text("tok")
    got = load_secrets(["artifactory_token"], environ={"MODELHUB_SECRETS_DIR": str(tmp_path)})
    assert got["artifactory_token"].reveal() == "tok"


def test_every_missing_or_empty_secret_is_named_in_one_error(tmp_path):
    (tmp_path / "empty_one").write_text("")
    with pytest.raises(StartupError) as err:
        load_secrets(["gone_one", "empty_one"], directory=tmp_path)
    text = str(err.value)
    assert "gone_one" in text and "empty_one" in text


def test_an_unreadable_secret_is_named_not_its_content(tmp_path):
    import os
    import sys

    if sys.platform == "win32" or os.geteuid() == 0:
        pytest.skip("permission test needs a non-root POSIX user")
    f = tmp_path / "locked"
    f.write_text(V2)
    f.chmod(0)
    with pytest.raises(StartupError) as err:
        load_secrets(["locked"], directory=tmp_path)
    assert "locked" in str(err.value) and V2 not in str(err.value)
    f.chmod(0o600)


def test_a_secret_name_cannot_escape_the_folder(tmp_path):
    with pytest.raises(StartupError):
        load_secrets(["../evil"], directory=tmp_path)


SPECS = [
    Setting("MODELHUB_REALM_ISSUER", str, required=True),
    Setting("MODELHUB_LOG_LEVEL", str, default="info"),
    Setting("MODELHUB_POOL", int, default=10, minimum=1),
    Setting("MODELHUB_FLAG", bool, default=False),
    Setting("MODELHUB_CONNECT_TIMEOUT", float, default=5.0, minimum=0, exclusive=True),
]


def test_defaults_and_values_are_typed():
    cfg, _ = load_config(
        SPECS,
        [],
        environ={
            "MODELHUB_REALM_ISSUER": "https://k/r",
            "MODELHUB_POOL": "7",
            "MODELHUB_FLAG": "true",
        },
    )
    assert cfg["MODELHUB_POOL"] == 7
    assert cfg["MODELHUB_FLAG"] is True
    assert cfg["MODELHUB_LOG_LEVEL"] == "info"
    assert cfg["MODELHUB_CONNECT_TIMEOUT"] == 5.0


def test_every_bad_setting_is_named_with_its_expected_type_never_its_value():
    with pytest.raises(StartupError) as err:
        load_config(
            SPECS,
            [],
            environ={"MODELHUB_POOL": "lots-of-secret-ish", "MODELHUB_CONNECT_TIMEOUT": "0"},
        )
    text = str(err.value)
    assert "MODELHUB_REALM_ISSUER" in text  # missing
    assert "MODELHUB_POOL" in text and "int" in text
    assert "MODELHUB_CONNECT_TIMEOUT" in text  # zero is refused
    assert "lots-of-secret-ish" not in text


def test_settings_and_secrets_problems_are_reported_together(tmp_path):
    with pytest.raises(StartupError) as err:
        load_config(SPECS, ["nope"], environ={"MODELHUB_SECRETS_DIR": str(tmp_path)})
    text = str(err.value)
    assert "MODELHUB_REALM_ISSUER" in text and "nope" in text


def test_a_minimum_is_enforced():
    with pytest.raises(StartupError):
        load_config(SPECS, [], environ={"MODELHUB_REALM_ISSUER": "x", "MODELHUB_POOL": "0"})


def test_the_shared_timeouts_default_to_the_contract_values():
    from modelhub_common.config import SHARED_SETTINGS

    cfg, _ = load_config(SHARED_SETTINGS, [], environ={"MODELHUB_REALM_ISSUER": "https://k/r"})
    assert cfg["MODELHUB_CONNECT_TIMEOUT"] == 5
    assert cfg["MODELHUB_READ_TIMEOUT"] == 30
    assert cfg["MODELHUB_PIECE_UPLOAD_TIMEOUT"] == 600
    assert cfg["MODELHUB_AUDIENCE"] == "modelhub"
