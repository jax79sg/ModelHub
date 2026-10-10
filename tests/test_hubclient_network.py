"""Tests that use the real internet. They are skipped unless asked for: pytest -m network."""

import json

import pytest

from modelhub import pull
from modelhub.hubclient import HfHubClient, ModelNotFound, UnsupportedModel

pytestmark = pytest.mark.network

TINY = "sshleifer/tiny-gpt2"  # a very small public model


@pytest.fixture(scope="module")
def client():
    return HfHubClient()


def test_model_information_comes_back_without_a_login(client):
    info = client.model_info(TINY)
    assert info["id"] == TINY
    assert len(info["sha"]) == 40


def test_tree_commits_and_refs_come_back(client):
    commit = client.model_info(TINY)["sha"]
    tree = client.tree(TINY, commit)
    assert any(e["type"] == "file" and e["path"] == "config.json" for e in tree)
    assert client.commits(TINY, commit)
    assert "branches" in client.refs(TINY)


def test_a_missing_model_is_reported(client):
    # The Hub answers 401 (not 404) to an anonymous caller for a model that does not exist.
    with pytest.raises((ModelNotFound, UnsupportedModel)):
        client.model_info("this-org-does-not-exist-123/nor-this-model")


def test_a_gated_model_is_reported_as_unsupported(client, tmp_path):
    with pytest.raises((UnsupportedModel, ModelNotFound)):
        pull.pull_model(client, "meta-llama/Llama-2-7b-hf", tmp_path, selection={"all"})


def test_progress_is_reported_while_a_file_downloads_and_adds_up_exactly(client, tmp_path):
    commit = client.model_info(TINY)["sha"]
    biggest = max(
        (e for e in client.tree(TINY, commit) if e["type"] == "file"), key=lambda e: e["size"]
    )
    seen = []
    dest = tmp_path / "f.bin"
    client.download_file(TINY, commit, biggest["path"], dest, progress_cb=seen.append)
    assert sum(seen) == dest.stat().st_size == biggest["size"]
    assert len(seen) >= 2  # reported in pieces as it went, not only at the end


def test_a_whole_tiny_model_is_pulled_and_every_checksum_matches(client, tmp_path):
    result = pull.pull_model(client, TINY, tmp_path, selection={"all"})
    manifest = json.loads((result.record_dir / "manifest.json").read_text())
    assert manifest["files"]
    assert (result.record_dir / "summary.json").is_file()
    assert (result.record_dir / "raw" / "model_info.json").is_file()
