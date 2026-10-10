"""Exit status (contract C4): 0 everything asked for was done, 1 at least one item failed,
2 the command could not run (wrong options, missing input, no room, folder in use)."""

import pytest
from conftest import COMMIT, TINY_FILES, FakeHub
from typer.testing import CliRunner

from modelhub import cli, fsutil, signing
from modelhub.hubclient import TransientHubError

runner = CliRunner()


@pytest.fixture
def hub():
    hub = FakeHub()
    hub.add_model("org/tiny", dict(TINY_FILES))
    return hub


@pytest.fixture
def run(tmp_path, hub, monkeypatch, home):
    monkeypatch.setattr(cli, "make_hub_client", lambda token=None: hub)
    monkeypatch.setattr("modelhub.download.time.sleep", lambda s: None)

    def _run(*args, input=None):
        return runner.invoke(
            cli.app, [str(a) for a in args], input=input, env={"MODELHUB_HOME": str(home)}
        )

    return _run


def test_status_zero_when_everything_asked_for_was_done(run, tmp_path):
    assert run("--version").exit_code == 0
    assert run("pull", "org/tiny", "--work", tmp_path / "w", "--type", "all").exit_code == 0
    assert run("pull", "org/tiny", "--work", tmp_path / "w").exit_code == 0  # shows the types


def test_status_one_when_an_item_failed_but_others_were_still_done(run, tmp_path, hub):
    hub.add_model("org/other", {"README.md": b"r", "w.safetensors": b"w" * 30}, commit="b" * 40)
    hub.failures["config.json"] = [TransientHubError("down")] * 99
    result = run("pull", "org/tiny", "org/other", "--work", tmp_path / "w", "--type", "all")
    assert result.exit_code == 1
    assert (tmp_path / "w/models/org/other/commits" / ("b" * 40) / "manifest.json").is_file()


def test_status_one_when_nothing_matched_the_chosen_type(run, tmp_path):
    assert run("pull", "org/tiny", "--work", tmp_path / "w", "--type", "gguf").exit_code == 1


@pytest.mark.parametrize(
    "args",
    [
        ["pull", "--work", "w", "--type", "all"],  # no model named
        ["pull", "org/tiny", "--work", "w", "--type", "nonsense"],  # an unknown file type
        ["pull", "org/tiny", "--work", "w", "--workers", "0"],  # a count that cannot work
        ["no-such-command"],
    ],
)
def test_status_two_when_the_command_could_not_run(run, tmp_path, args, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert run(*args).exit_code == 2


def test_status_two_when_the_folder_is_in_use(run, tmp_path):
    record = tmp_path / "w/models/org/tiny/commits" / COMMIT
    with fsutil.RunLock(record):
        assert run("pull", "org/tiny", "--work", tmp_path / "w", "--type", "all").exit_code == 2


def test_bundle_statuses(run, pulled, key_id, tmp_path, monkeypatch):
    out = tmp_path / "out"
    good = ["bundle", pulled, "--out", out, "--piece-size", "8KiB", "--key", key_id]
    assert run(*good).exit_code == 0
    monkeypatch.setattr(fsutil, "free_bytes", lambda path: 1)
    no_room = ["bundle", pulled, "--out", tmp_path / "o2", "--piece-size", "8KiB", "--key", key_id]
    assert run(*no_room).exit_code == 2  # not enough room
    monkeypatch.undo()
    assert run("bundle", pulled, "--out", tmp_path / "o3", "--key", key_id).exit_code == 2
    (pulled / "files" / "config.json").write_bytes(b"changed")
    assert run(*good).exit_code == 1  # the record changed


def test_bundle_status_two_when_there_is_no_signing_key(run, pulled, tmp_path):
    result = run("bundle", pulled, "--out", tmp_path / "o", "--piece-size", "8KiB")
    assert result.exit_code == 2
    assert "no signing key" in result.output


def test_verify_unpack_and_list_statuses(run, bundle_dir, tmp_path):
    assert run("verify", bundle_dir).exit_code == 0
    assert run("unpack", bundle_dir, "--store", tmp_path / "s").exit_code == 0
    assert run("list", tmp_path / "s").exit_code == 0
    assert run("list", tmp_path / "missing").exit_code == 2
    assert run("verify", tmp_path / "nothing-here").exit_code == 2
    victim = next(bundle_dir.glob("*.part-000001"))
    victim.write_bytes(b"x")
    assert run("verify", bundle_dir).exit_code == 1
    assert run("unpack", bundle_dir, "--store", tmp_path / "s2").exit_code == 1


def test_key_statuses(run, tmp_path):
    assert run("key", "create").exit_code == 0
    assert run("key", "export", "nonexistent", "--out", tmp_path / "p.json").exit_code == 1
    assert signing.list_keys()
