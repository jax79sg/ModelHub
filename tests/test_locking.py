import subprocess
import sys
import textwrap
import time

import pytest
from conftest import COMMIT
from typer.testing import CliRunner

from modelhub import cli, fsutil

runner = CliRunner()


def test_a_second_run_on_the_same_folder_is_refused(tmp_path):
    with fsutil.RunLock(tmp_path), pytest.raises(fsutil.LockedError), fsutil.RunLock(tmp_path):
        pass


def test_the_lock_is_released_when_the_run_ends(tmp_path):
    with fsutil.RunLock(tmp_path):
        pass
    with fsutil.RunLock(tmp_path):
        pass


def test_a_killed_run_does_not_leave_the_folder_locked(tmp_path):
    code = textwrap.dedent(
        f"""
        import sys, time
        from modelhub import fsutil
        with fsutil.RunLock({str(tmp_path)!r}):
            print("locked", flush=True)
            time.sleep(60)
        """
    )
    child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "locked"
        with pytest.raises(fsutil.LockedError), fsutil.RunLock(tmp_path):
            pass
    finally:
        child.kill()
        child.wait()
    time.sleep(0.1)
    with fsutil.RunLock(tmp_path):  # killed run: lock gone with it
        pass


def test_the_command_line_reports_a_folder_in_use_and_stops(tmp_path, fake_hub, monkeypatch):
    monkeypatch.setattr(cli, "make_hub_client", lambda token=None: fake_hub)
    record = tmp_path / "w" / "models" / "org" / "tiny" / "commits" / COMMIT
    with fsutil.RunLock(record):
        result = runner.invoke(
            cli.app, ["pull", "org/tiny", "--work", str(tmp_path / "w"), "--type", "all"]
        )
    assert result.exit_code == 2
    assert "another run" in result.output
    assert fake_hub.downloads() == []
