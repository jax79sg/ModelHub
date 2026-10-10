"""The automatic checks (CI): they run on GitHub, so here the files are checked so that they
cannot silently stop enforcing the agreed gates (NFR7.2, NFR7.3, FR8.1)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
RELEASE = (ROOT / ".github" / "workflows" / "release.yml").read_text()


def test_checks_run_on_pull_requests_and_on_main():
    assert "pull_request:" in CI and "branches: [main]" in CI


def test_lint_and_format_gates_are_enforced():
    assert "ruff check ." in CI and "ruff format --check ." in CI


def test_tests_run_on_linux_windows_and_macos_with_oldest_and_newest_python():
    for name in ("ubuntu-latest", "windows-latest", "macos-latest", '"3.10"', '"3.12"'):
        assert name in CI
    assert "pytest" in CI


def test_the_linux_program_is_built_on_an_old_system_and_started_on_an_older_one():
    assert "almalinux:8" in CI and "ubuntu:20.04" in CI


def test_both_programs_are_built_and_driven_through_the_whole_workflow():
    assert CI.count("packaging/build.py pyinstaller") >= 2
    assert CI.count("packaging/roundtrip_smoke.py") >= 2
    assert "windows-latest" in CI and "modelhub-windows-x86_64.exe" in CI
    assert "modelhub-linux-x86_64" in CI


def test_an_offline_install_pack_is_built_per_system():
    assert "pip wheel" in CI or "offline_pack" in CI
    assert (ROOT / "packaging" / "offline_pack.py").exists()


def test_a_tagged_version_publishes_the_files_to_a_release():
    assert "tags:" in RELEASE and "v*" in RELEASE
    assert "contents: write" in RELEASE
    assert "gh release" in RELEASE or "action-gh-release" in RELEASE


def test_the_release_reuses_the_checks_instead_of_copying_them():
    assert "workflow_call" in CI and "uses: ./.github/workflows/ci.yml" in RELEASE


def test_the_speed_benchmark_is_not_automatic():
    assert "benchmark_download" not in CI and "benchmark_download" not in RELEASE
