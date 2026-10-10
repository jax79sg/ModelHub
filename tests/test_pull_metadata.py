import json

import pytest
from conftest import COMMIT, TINY_FILES, FakeHub
from typer.testing import CliRunner

from modelhub import cli, pull
from modelhub.hubclient import ModelNotFound, UnsupportedModel

runner = CliRunner()
STAMP = "2026-03-04T05:06:07Z"


def record_dir(tmp_path):
    return tmp_path / "models" / "org" / "tiny" / "commits" / COMMIT


def test_raw_hub_responses_are_kept_exactly_as_returned(fake_hub, tmp_path):
    pull.pull_model(fake_hub, "org/tiny", tmp_path, selection={"all"}, now=lambda: STAMP)
    raw = record_dir(tmp_path) / "raw"
    model = fake_hub.models["org/tiny"]
    assert json.loads((raw / "model_info.json").read_text()) == model["info"]
    assert json.loads((raw / "tree.json").read_text()) == model["tree"]
    assert json.loads((raw / "commits.json").read_text()) == model["commits"]
    assert json.loads((raw / "refs.json").read_text()) == model["refs"]


def test_capture_time_is_recorded_in_the_manifest_and_the_summary(fake_hub, tmp_path):
    pull.pull_model(fake_hub, "org/tiny", tmp_path, selection={"all"}, now=lambda: STAMP)
    root = record_dir(tmp_path)
    assert json.loads((root / "manifest.json").read_text())["captured_at"] == STAMP
    assert json.loads((root / "summary.json").read_text())["captured_at"] == STAMP


def test_summary_holds_the_model_page_information(fake_hub, tmp_path):
    pull.pull_model(fake_hub, "org/tiny", tmp_path, selection={"all"}, now=lambda: STAMP)
    result = json.loads((record_dir(tmp_path) / "summary.json").read_text())
    assert result["card"]["license"] == "mit"
    assert result["stats"]["downloads"] == 1234
    assert result["readme"]["original"] == "files/README.md"
    assert {f["path"] for f in result["files"]} == set(TINY_FILES)


def test_manifest_keeps_the_hub_checksum_and_scan_result(fake_hub, tmp_path):
    pull.pull_model(fake_hub, "org/tiny", tmp_path, selection={"all"})
    manifest = json.loads((record_dir(tmp_path) / "manifest.json").read_text())
    weights = next(f for f in manifest["files"] if f["path"] == "model.safetensors")
    assert weights["hub_sha256"] == weights["sha256"]
    assert weights["scan"] == {"status": "safe"}


def test_a_requested_version_is_asked_for_and_recorded(fake_hub, tmp_path):
    pull.pull_model(fake_hub, "org/tiny", tmp_path, revision="v1.0", selection={"all"})
    assert ("model_info", "org/tiny", "v1.0") in fake_hub.calls
    manifest = json.loads((record_dir(tmp_path) / "manifest.json").read_text())
    assert manifest["requested_revision"] == "v1.0"
    assert manifest["commit"] == COMMIT


def test_default_version_is_main(fake_hub, tmp_path):
    pull.pull_model(fake_hub, "org/tiny", tmp_path, selection={"all"})
    manifest = json.loads((record_dir(tmp_path) / "manifest.json").read_text())
    assert manifest["requested_revision"] == "main"


@pytest.mark.parametrize("flag", [{"private": True}, {"gated": "manual"}, {"gated": "auto"}])
def test_private_and_gated_models_are_refused_and_nothing_is_written(tmp_path, flag):
    hub = FakeHub()
    hub.add_model("org/closed", {"README.md": b"x"}, **flag)
    with pytest.raises(UnsupportedModel):
        pull.pull_model(hub, "org/closed", tmp_path, selection={"all"})
    assert hub.downloads() == []
    assert not (tmp_path / "models").exists()


def test_a_missing_model_is_reported(fake_hub, tmp_path):
    with pytest.raises(ModelNotFound):
        pull.pull_model(fake_hub, "org/absent", tmp_path, selection={"all"})


def test_licence_file_is_found_and_named_in_the_summary(tmp_path):
    hub = FakeHub()
    hub.add_model("org/tiny", {"README.md": b"r", "LICENSE": b"terms", "m.safetensors": b"w" * 10})
    pull.pull_model(hub, "org/tiny", tmp_path, selection={"all"})
    result = json.loads((record_dir(tmp_path) / "summary.json").read_text())
    assert result["license"] == {"name": "mit", "file": "files/LICENSE", "text_available": True}


def test_no_licence_file_is_recorded_as_text_not_available(fake_hub, tmp_path):
    pull.pull_model(fake_hub, "org/tiny", tmp_path, selection={"all"})
    result = json.loads((record_dir(tmp_path) / "summary.json").read_text())
    assert result["license"] == {"name": "mit", "file": None, "text_available": False}


@pytest.fixture
def run(tmp_path, monkeypatch):
    hub = FakeHub()
    hub.add_model("org/tiny", dict(TINY_FILES))
    hub.add_model("org/closed", {"README.md": b"x"}, gated="manual")
    hub.add_model("org/second", {"README.md": b"y", "w.safetensors": b"z" * 20}, commit="e" * 40)
    monkeypatch.setattr(cli, "make_hub_client", lambda token=None: hub)

    def _run(*args):
        return runner.invoke(
            cli.app, [str(a) for a in args], env={"MODELHUB_HOME": str(tmp_path / "h")}
        )

    _run.hub = hub
    return _run


def test_cli_run_with_one_gated_model_fetches_the_others_and_ends_non_zero(run, tmp_path):
    result = run(
        "pull", "org/tiny", "org/closed", "org/second", "--work", tmp_path / "w", "--type", "all"
    )
    assert result.exit_code == 1
    assert "org/closed" in result.output and "gated" in result.output
    fetched = {c[1] for c in run.hub.calls if c[0] == "download"}
    assert fetched == {"org/tiny", "org/second"}


def test_cli_reports_a_missing_model(run, tmp_path):
    result = run("pull", "org/absent", "--work", tmp_path / "w", "--type", "all")
    assert result.exit_code == 1
    assert "org/absent" in result.output
