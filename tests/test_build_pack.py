"""The server pack is assembled from a fixed list, signed, and never holds the smoke-test files."""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from modelhub import serverpack, signing

DEPLOY = Path(__file__).resolve().parent.parent / "deploy"
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="the pack is built with bash")

DOCKER = """#!/usr/bin/env bash
case "$1 $2" in
  "image inspect")
    if [[ "$*" == *"modelhub/${MISSING:-none}:"* ]]; then exit 1; fi
    if [[ "$*" == *RepoDigests* ]]; then echo "postgres@sha256:$(printf 'a%.0s' {1..64})"; fi
    if [[ "$*" == *".Id"* ]]; then echo "sha256:$(printf 'b%.0s' {1..64})"; fi ;;
esac
case "$1" in save) head -c 2000 /dev/zero | tr '\\0' 'x' ;; esac
exit 0
"""


@pytest.fixture
def tools(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "docker").write_text(DOCKER)
    (bin_dir / "modelhub").write_text(
        f'#!/usr/bin/env bash\nexec "{sys.executable}" -m modelhub "$@"\n'
    )
    for tool in bin_dir.iterdir():
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    return bin_dir


def build(tools, out, home, **env):
    full = {
        **os.environ,
        "PATH": f"{tools}:{os.environ['PATH']}",
        "MODELHUB_HOME": str(home),
        "RELEASE": "1.2.3",
        "OUT": str(out),
        **env,
    }
    return subprocess.run(
        ["bash", str(DEPLOY / "build-pack.sh")],
        env=full,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def key(home, key_id):
    doc = signing.find_own_key(key_id)
    signing.trust_key(doc, doc["fingerprint"])
    return key_id


def test_the_pack_holds_the_images_the_settings_and_the_operator_files(tools, tmp_path, home, key):
    out = tmp_path / "pack"
    done = build(tools, out, home, KEY_ID=key)
    assert done.returncode == 0, done.stderr
    names = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    for expected in (
        "compose.yaml",
        "env.example",
        "ops.sh",
        "README.md",
        "release.env",
        "images/catalog.tar.gz",
        "images/artifactory-service.tar.gz",
        "images/portal.tar.gz",
        "images/proxy.tar.gz",
        "images/postgres.tar.gz",
        "images/postgres.digest",
        "SHA256SUMS",
        "SHA256SUMS.sig",
    ):
        assert expected in names, expected
    env = (out / "release.env").read_text()
    assert "MODELHUB_VERSION=1.2.3" in env and "POSTGRES_IMAGE=modelhub/postgres:1.2.3" in env
    assert (out / "images" / "postgres.digest").read_text().startswith("postgres@sha256:")
    assert serverpack.verify_pack(out) == []


def test_no_stand_in_or_smoke_file_goes_into_a_pack(tools, tmp_path, home, key):
    out = tmp_path / "pack"
    assert build(tools, out, home, KEY_ID=key).returncode == 0
    listed = (out / "SHA256SUMS").read_text()
    for forbidden in ("smoke", "stand", "driver", "testkit", ".env", "secrets"):
        assert forbidden not in listed.lower().replace("release.env", "")


def test_the_pack_compose_file_does_not_mention_the_smoke_override():
    text = (DEPLOY / "compose.yaml").read_text().lower()
    for word in ("standins", "smoke", "modelhub.test"):
        assert word not in text
    base = yaml.safe_load(text)
    assert not ({"standins", "driver"} & set(base["services"]))
    smoke = yaml.safe_load((DEPLOY / "smoke" / "compose.smoke.yaml").read_text())
    assert {"standins", "driver"} <= set(smoke["services"])


def test_an_image_that_is_not_built_stops_the_build_naming_it(tools, tmp_path, home, key):
    done = build(tools, tmp_path / "pack", home, KEY_ID=key, MISSING="portal")
    assert done.returncode != 0 and "modelhub/portal:1.2.3 is not built" in done.stderr


def test_without_a_key_the_pack_is_left_unsigned_with_a_warning(tools, tmp_path, home):
    out = tmp_path / "pack"
    done = build(tools, out, home)
    assert done.returncode == 0 and "NOT signed" in done.stderr
    assert not (out / "SHA256SUMS").exists()
    assert serverpack.verify_pack(out)  # an unsigned pack never verifies


def test_a_changed_image_in_a_signed_pack_is_found(tools, tmp_path, home, key):
    out = tmp_path / "pack"
    assert build(tools, out, home, KEY_ID=key).returncode == 0
    shutil.copy(out / "images" / "portal.tar.gz", out / "images" / "portal.bak")
    (out / "images" / "portal.tar.gz").write_bytes(b"swapped")
    problems = serverpack.verify_pack(out)
    assert any("images/portal.tar.gz" in p for p in problems)
