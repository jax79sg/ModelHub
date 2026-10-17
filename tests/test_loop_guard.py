"""The hook that keeps work on the AI-DLC loop (docs/ai-dlc-working-agreement.md)."""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

LOOP = Path(__file__).resolve().parent.parent / ".claude" / "loop"
spec = importlib.util.spec_from_file_location("loop_guard", LOOP / "loop_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


@pytest.fixture
def project(tmp_path):
    engine = tmp_path / "aidlc" / "spaces" / "default" / "intents" / "i1" / ".aidlc-engine"
    engine.mkdir(parents=True)
    (engine / "engine-touch").write_text("{}")
    return tmp_path


def set_age(project, minutes):
    path = project / "aidlc/spaces/default/intents/i1/.aidlc-engine/engine-touch"
    stamp = time.time() - minutes * 60
    os.utime(path, (stamp, stamp))


def run(project, tool, tool_input, **env):
    return subprocess.run(
        [sys.executable, str(LOOP / "loop_guard.py")],
        input=json.dumps({"tool_name": tool, "tool_input": tool_input}),
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project), **env},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m x",
        "git push -u origin branch",
        "cd x && git merge origin/main",
        "gh pr create --title t",
        "gh pr merge 3 --squash",
        "gh api -X PUT repos/o/r/pulls/3/merge -f merge_method=squash",
    ],
)
def test_sending_work_out_is_blocked_when_the_engine_has_not_been_asked(project, command):
    set_age(project, 120)
    done = run(project, "Bash", {"command": command})
    assert done.returncode == 2
    assert "aidlc engine orchestrate next" in done.stderr and "120 minutes" in done.stderr


def test_the_same_commands_pass_after_a_recent_engine_call(project):
    set_age(project, 5)
    assert run(project, "Bash", {"command": "git push"}).returncode == 0


def test_writes_to_source_folders_are_blocked_but_the_framework_records_are_not(project):
    set_age(project, 120)
    blocked = run(project, "Write", {"file_path": str(project / "server/portal/app.py")})
    assert blocked.returncode == 2 and "server/portal/app.py" in blocked.stderr
    assert run(project, "Edit", {"file_path": str(project / "tests/test_x.py")}).returncode == 2
    assert (
        run(
            project, "Write", {"file_path": str(project / "aidlc/spaces/x/code-summary.md")}
        ).returncode
        == 0
    )
    assert run(project, "Write", {"file_path": str(project / ".claude/loop/x.py")}).returncode == 0


def test_reading_testing_and_the_engine_itself_are_never_blocked(project):
    set_age(project, 600)
    for command in (
        "ls",
        "git status",
        "git log --oneline",
        "pytest -q",
        "gh pr view 3",
        "gh pr checks 3",
        "gh api repos/o/r/pulls/3 --jq .state",
        "aidlc engine orchestrate next --resume",
        "aidlc engine status",
    ):
        assert run(project, "Bash", {"command": command}).returncode == 0, command
    assert run(project, "Read", {"file_path": str(project / "server/x.py")}).returncode == 0


def test_with_no_workflow_in_the_folder_nothing_is_blocked(tmp_path):
    assert run(tmp_path, "Bash", {"command": "git push"}).returncode == 0


def test_the_limit_can_be_changed(project):
    set_age(project, 20)
    assert (
        run(project, "Bash", {"command": "git push"}, AIDLC_LOOP_MAX_AGE_MINUTES="10").returncode
        == 2
    )
    assert (
        run(project, "Bash", {"command": "git push"}, AIDLC_LOOP_MAX_AGE_MINUTES="60").returncode
        == 0
    )


def test_unreadable_input_never_blocks(project):
    done = subprocess.run(
        [sys.executable, str(LOOP / "loop_guard.py")],
        input="not json",
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)},
        check=False,
    )
    assert done.returncode == 0


def test_the_status_line_shows_the_age_and_warns_when_it_is_too_long(project):
    set_age(project, 3)
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project), "PATH": "/usr/bin:/bin"}
    fresh = subprocess.run(
        [sys.executable, str(LOOP / "status_line.py")],
        input="{}",
        capture_output=True,
        text=True,
        env=env,
        check=False,
    ).stdout
    assert "engine asked 3m ago" in fresh and "⚠" not in fresh
    set_age(project, 90)
    late = subprocess.run(
        [sys.executable, str(LOOP / "status_line.py")],
        input="{}",
        capture_output=True,
        text=True,
        env=env,
        check=False,
    ).stdout
    assert "⚠" in late and "off the AI-DLC loop" in late
