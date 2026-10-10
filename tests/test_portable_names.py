import pytest
from conftest import FakeHub

from modelhub import fsutil, pull


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("CON", "reserved"),
        ("nul.txt", "reserved"),
        ("sub/COM1.json", "reserved"),
        ("a:b.txt", "forbidden character"),
        ("what?.txt", "forbidden character"),
        ("trailing.", "ends with a dot or space"),
        ("trailing ", "ends with a dot or space"),
        ("x" * 256, "too long"),
        ("d/" * 130 + "f.txt", "too long"),
    ],
)
def test_names_windows_cannot_hold_are_found_with_a_reason(name, reason):
    problems = fsutil.windows_name_problems(name)
    assert problems and any(reason in p for p in problems)


@pytest.mark.parametrize(
    "name", ["config.json", "sub/dir/model-00001.safetensors", "ünïcode.txt", "a b.txt"]
)
def test_ordinary_names_have_no_problems(name):
    assert fsutil.windows_name_problems(name) == []


def hub_with_awkward_names():
    hub = FakeHub()
    hub.add_model(
        "org/tiny", {"README.md": b"r", "ok.json": b"{}", "aux.txt": b"x", "a:b.txt": b"y"}
    )
    return hub


def test_pull_on_linux_warns_about_names_windows_cannot_hold_but_keeps_them(tmp_path, monkeypatch):
    monkeypatch.setattr(fsutil, "IS_WINDOWS", False)
    result = pull.pull_model(hub_with_awkward_names(), "org/tiny", tmp_path, selection={"all"})
    assert set(result.name_warnings) == {"aux.txt", "a:b.txt"}
    assert (result.record_dir / "files" / "aux.txt").is_file()  # never renamed, never dropped


def test_pull_on_windows_fails_those_files_by_name_and_never_renames_them(tmp_path, monkeypatch):
    monkeypatch.setattr(fsutil, "IS_WINDOWS", True)
    with pytest.raises(pull.PullIncomplete) as error:
        pull.pull_model(hub_with_awkward_names(), "org/tiny", tmp_path, selection={"all"})
    failed = {f["path"]: f["reason"] for f in error.value.failed}
    assert set(failed) == {"aux.txt", "a:b.txt"}
    assert "Windows" in failed["aux.txt"]
    files = tmp_path / "models" / "org" / "tiny" / "commits"
    assert not list(files.rglob("aux*"))
