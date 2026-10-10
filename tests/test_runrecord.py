import json

import pytest
from conftest import COMMIT, TINY_FILES, FakeHub
from typer.testing import CliRunner

from modelhub import __version__, bundle, cli, runrecord, signing, unpack
from modelhub.hubclient import TransientHubError

runner = CliRunner()
SECRET = "hf_RecordSecretToken1234567890"


def test_the_record_carries_version_platform_times_and_a_count_of_each_outcome(tmp_path):
    rec = runrecord.RunRecord("pull")
    rec.add("org/tiny", "fetched", size=10, seconds=0.5, retries=1)
    rec.add("org/tiny", "skipped", size=3)
    rec.add("org/other", "failed", reason="down")
    path = rec.write(tmp_path / "run-record.json")
    doc = json.loads(path.read_text())
    assert doc["format_version"] and doc["tool_version"] == __version__
    assert doc["command"] == "pull"
    assert {"system", "machine", "python"} <= set(doc["platform"])
    assert doc["started_at"].endswith("Z") and doc["finished_at"].endswith("Z")
    assert doc["summary"] == {"fetched": 1, "skipped": 1, "failed": 1}
    assert doc["items"][0] == {
        "model": "org/tiny",
        "status": "fetched",
        "size": 10,
        "seconds": 0.5,
        "retries": 1,
    }


def test_secrets_are_hidden_in_the_record(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", SECRET)
    rec = runrecord.RunRecord("pull")
    rec.add("m", "failed", reason=f"Authorization: Bearer {SECRET}")
    text = rec.write(tmp_path / "r.json").read_text()
    assert SECRET not in text and "[token hidden]" in text


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


def test_pull_writes_a_record_listing_every_file_fetched(run, tmp_path):
    result = run("pull", "org/tiny", "--work", tmp_path / "w", "--type", "all")
    assert result.exit_code == 0, result.output
    doc = json.loads((tmp_path / "w" / "run-record.json").read_text())
    names = {i["name"] for i in doc["items"] if i["status"] == "fetched"}
    assert names == set(TINY_FILES)
    assert doc["summary"]["fetched"] == len(TINY_FILES)
    assert all("seconds" in i and "size" in i for i in doc["items"] if i["status"] == "fetched")


def test_pull_records_skipped_failed_and_unsupported_items(run, tmp_path, hub):
    hub.add_model("org/closed", {"README.md": b"x"}, gated="manual")
    run("pull", "org/tiny", "--work", tmp_path / "w", "--type", "all")  # first pass fetches all
    hub.failures["config.json"] = [TransientHubError("down")] * 99
    (tmp_path / "w/models/org/tiny/commits" / COMMIT / "files/config.json").unlink()
    result = run("pull", "org/tiny", "org/closed", "--work", tmp_path / "w", "--type", "all")
    assert result.exit_code == 1
    doc = json.loads((tmp_path / "w" / "run-record.json").read_text())
    by_status = {}
    for item in doc["items"]:
        by_status.setdefault(item["status"], []).append(item)
    assert any(i["name"] == "model.safetensors" for i in by_status["skipped"])
    assert (
        by_status["failed"][0]["name"] == "config.json"
        and "down" in by_status["failed"][0]["reason"]
    )
    assert by_status["unsupported"][0]["model"] == "org/closed"


def test_pull_records_retries_and_failed_pictures(run, tmp_path, hub, picture_server):
    hub.add_model("org/pics", {"README.md": f"![x]({picture_server.base}/none.png)".encode()})
    hub.failures["README.md"] = [TransientHubError("blip")] * 2
    result = run("pull", "org/pics", "--work", tmp_path / "w", "--type", "all")
    assert result.exit_code == 0, result.output
    doc = json.loads((tmp_path / "w" / "run-record.json").read_text())
    readme = next(i for i in doc["items"] if i["name"] == "README.md")
    assert readme["retries"] == 2
    picture = next(i for i in doc["items"] if i["status"] == "picture-failed")
    assert picture["name"].endswith("/none.png")


def test_the_record_is_written_even_when_the_run_fails(run, tmp_path, hub):
    hub.failures["config.json"] = [TransientHubError("down")] * 99
    result = run("pull", "org/tiny", "--work", tmp_path / "w", "--type", "all")
    assert result.exit_code == 1
    doc = json.loads((tmp_path / "w" / "run-record.json").read_text())
    assert doc["summary"]["failed"] == 1


def test_the_token_never_reaches_the_record(run, tmp_path, hub):
    hub.failures["config.json"] = [TransientHubError(f"Authorization: Bearer {SECRET}")] * 99
    run("pull", "org/tiny", "--work", tmp_path / "w", "--type", "all", env={"HF_TOKEN": SECRET})
    assert SECRET not in (tmp_path / "w" / "run-record.json").read_text()


def test_bundle_and_unpack_write_records_beside_their_output(run, pulled, key_id, tmp_path):
    out = tmp_path / "out"
    assert (
        run("bundle", pulled, "--out", out, "--piece-size", "8KiB", "--key", key_id).exit_code == 0
    )
    [record_file] = out.glob("*.run-record.json")
    doc = json.loads(record_file.read_text())
    assert doc["command"] == "bundle" and doc["summary"]["written"] >= 2
    doc2 = signing.export_public(key_id, tmp_path / "p.json")
    signing.trust_key(doc2, doc2["fingerprint"])
    assert run("unpack", out, "--store", tmp_path / "store").exit_code == 0
    store_doc = json.loads((tmp_path / "store" / "run-record.json").read_text())
    assert store_doc["command"] == "unpack" and store_doc["summary"]["unpacked"] == 1
    assert bundle and unpack  # the modules under test are imported on purpose
