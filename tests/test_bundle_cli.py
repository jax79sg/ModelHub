import pytest
from typer.testing import CliRunner

from modelhub import bundle, cli, fsutil

runner = CliRunner()


@pytest.fixture
def run(home, key_id):
    def _run(*args, input=None):
        return runner.invoke(
            cli.app, [str(a) for a in args], input=input, env={"MODELHUB_HOME": str(home)}
        )

    _run.key_id = key_id
    return _run


def test_the_size_and_piece_count_are_stated_before_anything_is_written(run, pulled, tmp_path):
    out = tmp_path / "out"
    result = run("bundle", pulled, "--out", out, "--piece-size", "4KiB", "--key", run.key_id)
    assert result.exit_code == 0, result.output
    size, count = bundle.plan_bundle(pulled, 4096)
    plan = f"{count} pieces"
    assert plan in result.output and f"{size} bytes" in result.output
    assert result.output.index("About") < result.output.index("Wrote")


def test_not_enough_space_stops_the_command_with_status_2(run, pulled, tmp_path, monkeypatch):
    monkeypatch.setattr(fsutil, "free_bytes", lambda path: 5)
    result = run(
        "bundle", pulled, "--out", tmp_path / "out", "--piece-size", "4KiB", "--key", run.key_id
    )
    assert result.exit_code == 2
    assert "bytes needed" in result.output


def test_a_record_changed_after_the_scan_is_refused_naming_the_file(run, pulled, tmp_path):
    (pulled / "files" / "config.json").write_bytes(b"changed")
    result = run(
        "bundle", pulled, "--out", tmp_path / "out", "--piece-size", "4KiB", "--key", run.key_id
    )
    assert result.exit_code == 1
    assert "changed: config.json" in result.output


def test_exactly_one_of_piece_size_or_interactive_is_required(run, pulled, tmp_path):
    neither = run("bundle", pulled, "--out", tmp_path / "o", "--key", run.key_id)
    both = run(
        "bundle", pulled, "--out", tmp_path / "o", "--piece-size", "4KiB", "--interactive",
        "--key", run.key_id,
    )  # fmt: skip
    assert neither.exit_code == 2 and both.exit_code == 2


def test_interactive_mode_asks_for_each_drive_in_turn(run, pulled, tmp_path):
    size = bundle.RESERVE + 16_384
    answers = "".join(f"{tmp_path / f'd{i}'}\n{size}\n" for i in range(1, 8))
    result = run(
        "bundle",
        pulled,
        "--out",
        tmp_path / "unused",
        "--interactive",
        "--key",
        run.key_id,
        input=answers,
    )
    assert result.exit_code == 0, result.output
    assert "Drive 1" in result.output and "Drive 2" in result.output
    assert (tmp_path / "d1").is_dir() and (tmp_path / "d2").is_dir()
    assert "Wrote" in result.output


def test_a_key_is_chosen_automatically_when_there_is_only_one(run, pulled, tmp_path):
    result = run("bundle", pulled, "--out", tmp_path / "out", "--piece-size", "4KiB")
    assert result.exit_code == 0, result.output
