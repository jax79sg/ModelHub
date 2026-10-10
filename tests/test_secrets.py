import os
import pickle
import sys

import pytest
from conftest import TINY_FILES, FakeHub
from typer.testing import CliRunner

from modelhub import bundle, cli, pull, signing, unpack

runner = CliRunner()
FAKE_TOKEN = "hf_FakeTokenForTests1234567890abc"


def every_file_text(*roots):
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file():
                yield path, path.read_bytes()


def test_the_private_key_never_appears_in_a_bundle_a_record_or_a_store(
    pulled, key_id, home, tmp_path
):
    out = tmp_path / "bundle"
    bundle.bundle_record(pulled, out, key_id, piece_size=4096)
    doc = signing.export_public(key_id, tmp_path / "pub.json")
    signing.trust_key(doc, doc["fingerprint"])
    unpack.unpack_bundle([out], tmp_path / "store")
    private_pem = (home / "keys" / f"{key_id}.key").read_bytes()
    body = b"".join(private_pem.splitlines()[1:-1])
    joined_pieces = b"".join(p.read_bytes() for p in sorted(out.glob("*.part-*")))
    for where, data in every_file_text(pulled.parent.parent.parent.parent, out, tmp_path / "store"):
        assert b"PRIVATE KEY" not in data, where
        assert body not in data, where
    assert body not in joined_pieces


def test_a_token_in_the_environment_never_reaches_any_output_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv("MODELHUB_HOME", str(tmp_path / "home"))
    hub = FakeHub()
    hub.add_model("org/tiny", dict(TINY_FILES))
    monkeypatch.setattr(cli, "make_hub_client", lambda token=None: hub)
    result = runner.invoke(
        cli.app, ["pull", "org/tiny", "--work", str(tmp_path / "w"), "--type", "all"]
    )
    assert result.exit_code == 0
    assert FAKE_TOKEN not in result.output
    for where, data in every_file_text(tmp_path / "w"):
        assert FAKE_TOKEN.encode() not in data, where


def test_no_model_file_is_ever_run_or_loaded(tmp_path):
    marker = tmp_path / "ran"

    class Evil:
        def __reduce__(self):
            return (os.mkdir, (str(marker),))  # would create the folder if the file were loaded

    evil_bytes = pickle.dumps(Evil())
    hub = FakeHub()
    hub.add_model("org/tiny", {"README.md": b"r", "pytorch_model.bin": evil_bytes})
    record = pull.pull_model(hub, "org/tiny", tmp_path / "w", selection={"all"}).record_dir
    assert not marker.exists()
    assert (record / "files" / "pytorch_model.bin").read_bytes() == evil_bytes  # copied untouched


@pytest.mark.skipif(sys.platform == "win32", reason="Windows access rules are checked there")
def test_the_private_key_file_stays_owner_only_after_a_second_key_is_made(home):
    first = signing.create_key("a")
    signing.create_key("b")
    for key in (home / "keys").glob("*.key"):
        assert key.stat().st_mode & 0o077 == 0, first["key_id"]
