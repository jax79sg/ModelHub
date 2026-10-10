import json
import shutil

import pytest
from conftest import COMMIT
from typer.testing import CliRunner

from modelhub import cli, store, unpack, verify

runner = CliRunner()


@pytest.fixture
def full_store(bundle_dir, tmp_path):
    unpack.unpack_bundle([bundle_dir], tmp_path / "store")
    return tmp_path / "store"


def test_list_shows_name_commit_capture_date_size_and_licence(full_store):
    [item] = store.list_models(full_store)
    assert item.model_id == "org/tiny"
    assert item.commit == COMMIT
    assert item.captured_at
    assert item.size and item.size > 20_000
    assert item.license == "mit"
    assert item.latest is True


def test_every_version_is_listed_and_only_one_is_marked_latest(full_store):
    second = "f" * 40
    shutil.copytree(
        full_store / "models/org/tiny/commits" / COMMIT,
        full_store / "models/org/tiny/commits" / second,
    )
    items = store.list_models(full_store)
    assert {i.commit for i in items} == {COMMIT, second}
    assert [i.latest for i in items if i.commit == COMMIT] == [True]
    assert [i.latest for i in items if i.commit == second] == [False]


def test_unpacking_an_older_version_again_does_not_move_latest_backwards(full_store):
    newer = "f" * 40
    root = full_store / "models/org/tiny"
    shutil.copytree(root / "commits" / COMMIT, root / "commits" / newer)
    manifest = json.loads((root / "commits" / newer / "manifest.json").read_text())
    manifest["captured_at"] = "2030-01-01T00:00:00Z"
    (root / "commits" / newer / "manifest.json").write_text(json.dumps(manifest))
    paths = store.StorePaths(full_store, "org/tiny")
    store.update_pointers(paths, newer, "main")
    assert (root / "latest").read_text().strip() == newer
    store.update_pointers(paths, COMMIT, "main")  # the older one again
    assert (root / "latest").read_text().strip() == newer


def test_models_with_one_or_two_part_names_are_both_found(tmp_path):
    for model_id in ("gpt2", "org/two"):
        folder = tmp_path / "models" / model_id / "commits" / ("1" * 40)
        folder.mkdir(parents=True)
        (folder / "summary.json").write_text(json.dumps({"captured_at": "2026-01-01T00:00:00Z"}))
    assert [i.model_id for i in store.list_models(tmp_path)] == ["gpt2", "org/two"]


def test_unreadable_summaries_do_not_stop_the_listing(full_store):
    (full_store / "models/org/tiny/commits" / COMMIT / "summary.json").write_text("{not json")
    [item] = store.list_models(full_store)
    assert item.model_id == "org/tiny" and item.size is None


def test_unfinished_unpacks_are_not_listed(full_store):
    (full_store / "models/org/tiny/commits" / f".{'a' * 40}.partial").mkdir()
    assert len(store.list_models(full_store)) == 1


@pytest.fixture
def run(home):
    def _run(*args):
        return runner.invoke(cli.app, [str(a) for a in args], env={"MODELHUB_HOME": str(home)})

    return _run


def test_cli_list_prints_one_line_per_version(run, full_store):
    result = run("list", full_store)
    assert result.exit_code == 0, result.output
    assert "org/tiny" in result.output and COMMIT[:12] in result.output
    assert "latest" in result.output and "mit" in result.output


def test_cli_list_of_an_empty_store_prints_nothing_and_succeeds(run, tmp_path):
    (tmp_path / "empty").mkdir()
    result = run("list", tmp_path / "empty")
    assert result.exit_code == 0 and result.output.strip() == ""


def test_cli_list_of_a_folder_that_does_not_exist_is_a_clear_error(run, tmp_path):
    result = run("list", tmp_path / "nowhere")
    assert result.exit_code == 2
    assert "no such folder" in result.output.lower()


def test_verify_checks_every_file_in_a_store_against_its_manifest(full_store):
    assert verify.verify_store(full_store) == []
    target = full_store / "models/org/tiny/commits" / COMMIT / "files" / "config.json"
    target.write_bytes(b"damaged")
    problems = verify.verify_store(full_store)
    assert [p.code for p in problems] == ["file-damaged"]
    assert "config.json" in problems[0].message


def test_cli_verify_accepts_a_store_folder(run, full_store):
    assert run("verify", full_store).exit_code == 0
    (full_store / "models/org/tiny/commits" / COMMIT / "files" / "config.json").unlink()
    result = run("verify", full_store)
    assert result.exit_code == 1 and "config.json" in result.output
