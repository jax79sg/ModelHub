"""The thin end-to-end slice: download side to air-gapped side, through every command."""

import json
import re

import pytest
from conftest import COMMIT, TINY_FILES
from typer.testing import CliRunner

from modelhub import cli

runner = CliRunner()


@pytest.fixture
def run(tmp_path, fake_hub, monkeypatch):
    monkeypatch.setattr(cli, "make_hub_client", lambda token=None: fake_hub)

    def _run(*args, home="home", input=None):
        env = {"MODELHUB_HOME": str(tmp_path / home)}
        return runner.invoke(cli.app, [str(a) for a in args], input=input, env=env)

    return _run


def fingerprint_of(output: str) -> str:
    return re.search(r"Fingerprint: (\S+)", output).group(1)


def key_id_of(output: str) -> str:
    return re.search(r"Created key (\S+)", output).group(1)


def make_signed_bundle(run, tmp_path, piece_size="4KB"):
    created = run("key", "create", "--name", "test")
    assert created.exit_code == 0, created.output
    key_id = key_id_of(created.output)
    pulled = run("pull", "org/tiny", "--work", tmp_path / "work", "--type", "all")
    assert pulled.exit_code == 0, pulled.output
    record = tmp_path / "work" / "models" / "org" / "tiny" / "commits" / COMMIT
    bundled = run(
        "bundle", record, "--out", tmp_path / "bundle", "--piece-size", piece_size, "--key", key_id
    )
    assert bundled.exit_code == 0, bundled.output
    pub = tmp_path / "public.json"
    exported = run("key", "export", key_id, "--out", pub)
    assert exported.exit_code == 0, exported.output
    return key_id, pub


def trust_on_other_side(run, pub):
    fp = fingerprint_of(run("key", "fingerprint", pub, home="airgap").output)
    return run("key", "trust", pub, home="airgap", input=fp + "\n")


def test_pull_writes_the_download_record(run, tmp_path):
    result = run("pull", "org/tiny", "--work", tmp_path / "work", "--type", "all")
    assert result.exit_code == 0, result.output
    rec = tmp_path / "work" / "models" / "org" / "tiny" / "commits" / COMMIT
    for name, data in TINY_FILES.items():
        assert (rec / "files" / name).read_bytes() == data
    manifest = json.loads((rec / "manifest.json").read_text())
    assert manifest["commit"] == COMMIT
    assert {f["path"] for f in manifest["files"]} == set(TINY_FILES)
    assert (rec / "raw" / "model_info.json").is_file()
    assert (rec / "summary.json").is_file()


def test_whole_path_from_download_to_listing(run, tmp_path):
    _, pub = make_signed_bundle(run, tmp_path)
    assert len(list((tmp_path / "bundle").glob("*.part-*"))) > 1  # really split into pieces
    assert trust_on_other_side(run, pub).exit_code == 0

    checked = run("verify", tmp_path / "bundle", home="airgap")
    assert checked.exit_code == 0, checked.output

    unpacked = run("unpack", tmp_path / "bundle", "--store", tmp_path / "store", home="airgap")
    assert unpacked.exit_code == 0, unpacked.output
    rebuilt = tmp_path / "store" / "models" / "org" / "tiny" / "commits" / COMMIT
    for name, data in TINY_FILES.items():
        assert (rebuilt / "files" / name).read_bytes() == data
    assert (tmp_path / "store" / "models" / "org" / "tiny" / "latest").read_text().strip() == COMMIT

    listed = run("list", tmp_path / "store", home="airgap")
    assert listed.exit_code == 0, listed.output
    assert "org/tiny" in listed.output
    assert COMMIT[:12] in listed.output


def test_untrusted_key_is_refused_and_nothing_is_rebuilt(run, tmp_path):
    make_signed_bundle(run, tmp_path)
    checked = run("verify", tmp_path / "bundle", home="airgap")
    assert checked.exit_code == 1
    assert "trust" in checked.output.lower()
    unpacked = run("unpack", tmp_path / "bundle", "--store", tmp_path / "store", home="airgap")
    assert unpacked.exit_code == 1
    assert not (tmp_path / "store" / "models").exists()


def test_bundle_pieces_join_by_hand_into_a_standard_archive(run, tmp_path):
    import tarfile

    make_signed_bundle(run, tmp_path)
    pieces = sorted((tmp_path / "bundle").glob("*.part-*"))
    joined = tmp_path / "joined.tar"
    with joined.open("wb") as out:
        for piece in pieces:
            out.write(piece.read_bytes())
    with tarfile.open(joined) as tar:
        names = tar.getnames()
    assert "manifest.json" in names
    assert "files/model.safetensors" in names


def test_version_option_prints_the_version(run):
    result = run("--version")
    assert result.exit_code == 0
    assert result.output.strip()
