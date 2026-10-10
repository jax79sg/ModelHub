"""The commands used inside the air-gapped environment make no network connection (NFR5.1,
NFR5.2): they must work on a computer with no route out, and need nothing from the internet."""

import subprocess
import sys
import textwrap

import pytest
from conftest import COMMIT
from typer.testing import CliRunner

from modelhub import cli, signing

runner = CliRunner()


def test_the_guard_itself_works(no_network):
    import socket

    with pytest.raises(AssertionError, match="network connection"):
        socket.create_connection(("example.com", 80))


def test_every_air_gapped_command_works_with_the_network_blocked(
    bundle_dir, tmp_path, home, no_network
):
    env = {"MODELHUB_HOME": str(home)}
    store_dir = tmp_path / "store"

    def run(*args, **kwargs):
        result = runner.invoke(cli.app, [str(a) for a in args], env=env, **kwargs)
        assert result.exit_code == 0, (args, result.output)
        return result

    run("verify", bundle_dir)
    run("unpack", bundle_dir, "--store", store_dir)
    assert COMMIT[:12] in run("list", store_dir).output
    run("verify", store_dir)  # a store checks out too
    created = run("key", "create", "--name", "second")
    key_id = created.output.split("Created key ")[1].split()[0]
    run("key", "list")
    run("key", "export", key_id, "--out", tmp_path / "second.json")
    fingerprint = run("key", "fingerprint", tmp_path / "second.json").output.split()[-1]
    run("key", "trust", tmp_path / "second.json", input=fingerprint + "\n")
    run("key", "untrust", key_id)


def test_the_air_gapped_commands_do_not_even_load_the_hugging_face_library(
    bundle_dir, tmp_path, home
):
    script = textwrap.dedent(
        f"""
        import os, sys, socket
        os.environ["MODELHUB_HOME"] = {str(home)!r}
        def refuse(*a, **k):
            raise AssertionError("network used")
        socket.socket.connect = refuse
        socket.create_connection = refuse
        from typer.testing import CliRunner
        from modelhub import cli
        runner = CliRunner()
        for args in (
            ["verify", {str(bundle_dir)!r}],
            ["unpack", {str(bundle_dir)!r}, "--store", {str(tmp_path / "s")!r}],
            ["list", {str(tmp_path / "s")!r}],
        ):
            result = runner.invoke(cli.app, args)
            assert result.exit_code == 0, (args, result.output)
        loaded = sorted(m for m in ("huggingface_hub", "httpx2", "hf_xet") if m in sys.modules)
        print("LOADED", loaded)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "LOADED []" in result.stdout, result.stdout


def test_a_stranger_key_is_still_refused_offline(pulled, tmp_path, home, no_network):
    from modelhub import bundle

    other = signing.create_key("stranger")
    out = tmp_path / "b"
    bundle.bundle_record(pulled, out, other["key_id"], piece_size=8192)
    result = runner.invoke(cli.app, ["verify", str(out)], env={"MODELHUB_HOME": str(home)})
    assert result.exit_code == 1
