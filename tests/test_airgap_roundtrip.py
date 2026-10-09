from typer.testing import CliRunner

from modelhub.cli import app
from modelhub.manifest import build_manifest

runner = CliRunner()
SHA = "a" * 40


def fake_pulled_repo(tmp_path):
    root = tmp_path / "pulled" / "org" / "name"
    (root / "snapshot").mkdir(parents=True)
    (root / "metadata").mkdir()
    (root / "snapshot" / "README.md").write_text("# hi")
    (root / "snapshot" / "model.safetensors").write_bytes(b"\x07" * 1000)
    (root / "metadata" / "repo_info.json").write_text("{}")
    m = build_manifest(root, "org/name", "model", SHA, "main")
    (root / "manifest.json").write_text(m.to_json())
    return root


def test_roundtrip_and_hf_cache(tmp_path):
    root = fake_pulled_repo(tmp_path)
    assert runner.invoke(app, ["verify", str(root)]).exit_code == 0

    tar = tmp_path / "x.tar"
    assert runner.invoke(app, ["bundle", str(root), "-o", str(tar)]).exit_code == 0

    dest, cache = tmp_path / "onprem", tmp_path / "cache"
    r = runner.invoke(app, ["unpack", str(tar), "-d", str(dest), "--hf-cache", str(cache)])
    assert r.exit_code == 0, r.output
    repo = cache / "models--org--name"
    assert (repo / "snapshots" / SHA / "model.safetensors").stat().st_size == 1000
    assert (repo / "refs" / "main").read_text() == SHA


def test_verify_detects_corruption(tmp_path):
    root = fake_pulled_repo(tmp_path)
    (root / "snapshot" / "model.safetensors").write_bytes(b"\x01" * 1000)
    r = runner.invoke(app, ["verify", str(root)])
    assert r.exit_code == 1
    assert "hash mismatch" in r.output
    assert runner.invoke(app, ["bundle", str(root), "-o", str(tmp_path / "x.tar")]).exit_code != 0


def test_corrupt_bundle_rejected(tmp_path):
    root = fake_pulled_repo(tmp_path)
    tar = tmp_path / "x.tar"
    runner.invoke(app, ["bundle", str(root), "-o", str(tar)])
    data = bytearray(tar.read_bytes())
    data[data.find(b"\x07" * 1000) + 500] ^= 0xFF  # flip a byte inside the weights payload
    tar.write_bytes(bytes(data))
    r = runner.invoke(app, ["unpack", str(tar), "-d", str(tmp_path / "d")])
    assert r.exit_code != 0
    assert not (tmp_path / "d").exists()
