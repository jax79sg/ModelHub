import pytest
from conftest import TINY_FILES, FakeHub
from typer.testing import CliRunner

from modelhub import cli, download, redact
from modelhub.hubclient import HfHubClient, TransientHubError

runner = CliRunner()
SECRET = "hf_" + "SeCrEt1234567890abcdefghij"


def test_the_token_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", SECRET)
    assert HfHubClient().token == SECRET


def test_redact_hides_the_environment_token_and_anything_shaped_like_one(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "plainsecretvalue")
    text = f"failed with plainsecretvalue and Bearer {SECRET} and again {SECRET}"
    cleaned = redact.redact(text)
    assert "plainsecretvalue" not in cleaned
    assert SECRET not in cleaned
    assert "[token hidden]" in cleaned


def test_redact_leaves_ordinary_text_alone(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert redact.redact("nothing to hide here") == "nothing to hide here"


@pytest.fixture
def run(tmp_path, monkeypatch):
    hub = FakeHub()
    hub.add_model("org/tiny", dict(TINY_FILES))
    seen = {}

    def make(token=None):
        seen["token"] = token
        return hub

    monkeypatch.setattr(cli, "make_hub_client", make)

    def _run(*args, input=None, env=None):
        merged = {"MODELHUB_HOME": str(tmp_path / "h")}
        merged.update(env or {})
        return runner.invoke(cli.app, [str(a) for a in args], input=input, env=merged)

    _run.hub, _run.seen = hub, seen
    return _run


def test_a_token_on_the_command_line_is_refused_with_an_explanation(run, tmp_path):
    result = run("pull", "org/tiny", "--work", tmp_path / "w", "--token", SECRET)
    assert result.exit_code == 2
    assert "HF_TOKEN" in result.output
    assert SECRET not in result.output


def test_a_hidden_prompt_can_supply_the_token(run, tmp_path):
    result = run(
        "pull",
        "org/tiny",
        "--work",
        tmp_path / "w",
        "--type",
        "all",
        "--ask-token",
        input="typed-secret\n",
    )
    assert result.exit_code == 0, result.output
    assert run.seen["token"] == "typed-secret"
    assert "typed-secret" not in result.output


def test_errors_never_show_the_token(run, tmp_path, monkeypatch):
    monkeypatch.setattr(download.time, "sleep", lambda seconds: None)  # skip the retry waits
    run.hub.failures["config.json"] = [
        TransientHubError(f"request failed, header Authorization: Bearer {SECRET}")
    ] * 99
    result = run(
        "pull", "org/tiny", "--work", tmp_path / "w", "--type", "all", env={"HF_TOKEN": SECRET}
    )
    assert result.exit_code == 1
    assert SECRET not in result.output
    assert "config.json" in result.output
