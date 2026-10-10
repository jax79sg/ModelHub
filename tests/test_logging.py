import re

import pytest
from conftest import TINY_FILES, FakeHub
from typer.testing import CliRunner

from modelhub import cli
from modelhub.hubclient import TransientHubError

runner = CliRunner()
LINE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ (DEBUG|INFO|WARNING|ERROR) ")


@pytest.fixture
def hub():
    hub = FakeHub()
    hub.add_model("org/tiny", dict(TINY_FILES))
    return hub


@pytest.fixture
def run(tmp_path, hub, monkeypatch, home):
    monkeypatch.setattr(cli, "make_hub_client", lambda token=None: hub)
    monkeypatch.setattr("modelhub.download.time.sleep", lambda s: None)

    def _run(*args, env=None):
        merged = {"MODELHUB_HOME": str(home), **(env or {})}
        return runner.invoke(cli.app, [str(a) for a in args], env=merged)

    return _run


def log_lines(folder):
    return (folder / "modelhub.log").read_text().splitlines()


def test_normal_runs_write_no_log_file(run, tmp_path):
    run("pull", "org/tiny", "--work", tmp_path / "w", "--type", "all")
    assert not (tmp_path / "w" / "modelhub.log").exists()


def test_verbose_writes_a_log_with_utc_times_beside_the_output(run, tmp_path):
    result = run("--verbose", "pull", "org/tiny", "--work", tmp_path / "w", "--type", "all")
    assert result.exit_code == 0, result.output
    lines = log_lines(tmp_path / "w")
    assert lines and all(LINE.match(line) for line in lines)
    text = "\n".join(lines)
    assert "model.safetensors" in text and "INFO" in text
    assert "DEBUG" not in text


def test_debug_writes_more_detail_than_verbose(run, tmp_path):
    run("--verbose", "pull", "org/tiny", "--work", tmp_path / "v", "--type", "all")
    run("--debug", "pull", "org/tiny", "--work", tmp_path / "d", "--type", "all")
    assert len(log_lines(tmp_path / "d")) > len(log_lines(tmp_path / "v"))
    assert "DEBUG" in "\n".join(log_lines(tmp_path / "d"))


def test_retries_are_logged_and_a_token_never_is(run, tmp_path, hub):
    secret = "hf_LogSecretToken1234567890abc"
    hub.failures["config.json"] = [TransientHubError(f"Authorization: Bearer {secret}")] * 2
    run(
        "--debug",
        "pull",
        "org/tiny",
        "--work",
        tmp_path / "w",
        "--type",
        "all",
        env={"HF_TOKEN": secret},
    )
    text = (tmp_path / "w" / "modelhub.log").read_text()
    assert "trying again" in text and "config.json" in text
    assert secret not in text


def test_bundle_and_unpack_log_beside_their_own_output(run, pulled, key_id, tmp_path, bundle_dir):
    out = tmp_path / "out"
    run("--verbose", "bundle", pulled, "--out", out, "--piece-size", "8KiB", "--key", key_id)
    assert any("piece" in line for line in log_lines(out))
    run("--verbose", "unpack", bundle_dir, "--store", tmp_path / "store")
    assert any("org/tiny" in line for line in log_lines(tmp_path / "store"))
