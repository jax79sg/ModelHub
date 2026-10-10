"""The single program file per system (FR8.1 to FR8.3). The builds themselves run on Linux and
Windows in the check step; here the definitions are tested so they cannot silently rot."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

import modelhub

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def load_build_module():
    spec = importlib.util.spec_from_file_location("build_program", ROOT / "packaging" / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_package_version_and_the_declared_version_agree():
    declared = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    assert modelhub.__version__ == declared


def test_the_command_is_installed_under_the_name_modelhub():
    scripts = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["scripts"]
    assert scripts == {"modelhub": "modelhub.cli:app"}


def test_running_the_package_as_a_module_prints_the_version():
    result = subprocess.run(
        [sys.executable, "-m", "modelhub", "--version"], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == f"modelhub {modelhub.__version__}"


def test_the_entry_script_starts_the_command_line():
    text = (ROOT / "packaging" / "entry.py").read_text()
    assert "from modelhub.cli import app" in text and "app()" in text


def test_the_entry_script_lets_a_packed_program_start_its_own_helper_processes():
    # Found by a real build: the progress-bar library starts a helper process by re-running the
    # program with Python-only flags. A packed program must answer those before its own options.
    text = (ROOT / "packaging" / "entry.py").read_text()
    assert "multiprocessing.freeze_support()" in text
    assert text.index("freeze_support") < text.index("app()")


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("Linux", "x86_64", "modelhub-linux-x86_64"),
        ("Windows", "AMD64", "modelhub-windows-x86_64.exe"),
        ("Windows", "x86_64", "modelhub-windows-x86_64.exe"),
    ],
)
def test_the_program_file_is_named_for_its_system(system, machine, expected):
    assert load_build_module().artifact_name(system, machine) == expected


@pytest.mark.parametrize("tool", ["pyinstaller", "nuitka"])
def test_both_build_commands_make_one_file_and_include_the_native_parts(tool):
    build = load_build_module()
    command = " ".join(build.command_for(tool, Path("out")))
    assert "--onefile" in command
    for part in build.NATIVE_PARTS:
        assert part in command, f"{tool} command does not mention {part}"
    assert "packaging" in command and "entry.py" in command


def test_the_native_parts_named_are_the_ones_the_tool_really_uses():
    build = load_build_module()
    assert set(build.NATIVE_PARTS) == {"hf_xet", "cryptography"}


def test_an_unknown_build_tool_is_refused():
    with pytest.raises(ValueError, match="unknown build tool"):
        load_build_module().command_for("magic", Path("out"))


def test_the_smoke_check_runs_the_file_with_a_scrubbed_environment(tmp_path):
    build = load_build_module()
    script = tmp_path / "fake-program"
    script.write_text(
        f"#!{sys.executable}\nimport os,sys\nprint('modelhub 9.9', 'PYTHONPATH' in os.environ)\n"
    )
    script.chmod(0o755)
    output = build.smoke_check(script, env={"PYTHONPATH": "/should/not/leak"})
    assert output.startswith("modelhub 9.9") and "True" not in output


def test_the_build_tools_are_an_optional_extra_not_a_normal_dependency():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert "pyinstaller" not in " ".join(project["dependencies"]).lower()
    assert any("pyinstaller" in d.lower() for d in project["optional-dependencies"]["build"])
