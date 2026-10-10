import pytest
from conftest import FakeHub
from typer.testing import CliRunner

from modelhub import cli, filetypes, pull

runner = CliRunner()

MULTI = {
    "README.md": b"# Multi\n",
    "config.json": b"{}\n",
    "LICENSE": b"licence text\n",
    "model.safetensors": b"s" * 3000,
    "pytorch_model.bin": b"b" * 2000,
    "tf_model.h5": b"h" * 1000,
}


@pytest.fixture
def multi_hub():
    hub = FakeHub()
    hub.add_model("org/multi", dict(MULTI))
    hub.add_model("org/other", {"README.md": b"# Other\n", "model.safetensors": b"o" * 500})
    return hub


def test_no_selection_downloads_nothing_and_returns_the_type_list(multi_hub, tmp_path):
    result = pull.pull_model(multi_hub, "org/multi", tmp_path, selection=None)
    assert result.fetched == []
    assert result.record_dir is None
    assert not (tmp_path / "models").exists()
    assert multi_hub.downloads() == []
    assert {g.type.key for g in result.groups} >= {"safetensors", "bin", "h5"}


def test_selecting_one_type_fetches_it_plus_the_small_files(multi_hub, tmp_path):
    result = pull.pull_model(multi_hub, "org/multi", tmp_path, selection={"safetensors"})
    assert set(result.fetched) == {"README.md", "config.json", "LICENSE", "model.safetensors"}
    assert "pytorch_model.bin" not in multi_hub.downloads()


def test_selecting_all_fetches_everything(multi_hub, tmp_path):
    result = pull.pull_model(multi_hub, "org/multi", tmp_path, selection={"all"})
    assert set(result.fetched) == set(MULTI)


def test_an_unknown_type_is_refused_before_any_download(multi_hub, tmp_path):
    with pytest.raises(filetypes.UnknownFileType):
        pull.pull_model(multi_hub, "org/multi", tmp_path, selection={"nope"})
    assert multi_hub.downloads() == []


def test_a_selection_that_matches_no_weights_fetches_nothing(multi_hub, tmp_path):
    result = pull.pull_model(multi_hub, "org/multi", tmp_path, selection={"gguf"})
    assert result.nothing_matched is True
    assert multi_hub.downloads() == []


@pytest.fixture
def run(tmp_path, multi_hub, monkeypatch):
    monkeypatch.setattr(cli, "make_hub_client", lambda token=None: multi_hub)

    def _run(*args):
        env = {"MODELHUB_HOME": str(tmp_path / "home")}
        return runner.invoke(cli.app, [str(a) for a in args], env=env)

    return _run


def test_cli_without_type_shows_types_with_explanations_and_stops(run, tmp_path, multi_hub):
    result = run("pull", "org/multi", "--work", tmp_path / "w")
    assert result.exit_code == 0, result.output
    assert "safetensors" in result.output
    assert "cannot contain runnable code" in result.output
    assert "--type" in result.output
    assert multi_hub.downloads() == []


def test_cli_with_two_types_fetches_both(run, tmp_path, multi_hub):
    result = run(
        "pull", "org/multi", "--work", tmp_path / "w", "--type", "safetensors", "--type", "h5"
    )
    assert result.exit_code == 0, result.output
    assert "tf_model.h5" in multi_hub.downloads()
    assert "pytorch_model.bin" not in multi_hub.downloads()


def test_cli_list_file_applies_one_selection_to_every_model(run, tmp_path, multi_hub):
    listing = tmp_path / "models.txt"
    listing.write_text("# my models\norg/multi\n\norg/other\n")
    result = run("pull", "--list", listing, "--work", tmp_path / "w", "--type", "safetensors")
    assert result.exit_code == 0, result.output
    fetched_models = {c[1] for c in multi_hub.calls if c[0] == "download"}
    assert fetched_models == {"org/multi", "org/other"}


def test_cli_list_file_without_type_shows_types_for_each_model_and_stops(run, tmp_path, multi_hub):
    listing = tmp_path / "models.txt"
    listing.write_text("org/multi\norg/other\n")
    result = run("pull", "--list", listing, "--work", tmp_path / "w")
    assert result.exit_code == 0, result.output
    assert "org/multi" in result.output and "org/other" in result.output
    assert multi_hub.downloads() == []


def test_cli_reports_when_a_selection_matches_nothing(run, tmp_path):
    result = run("pull", "org/multi", "--work", tmp_path / "w", "--type", "gguf")
    assert result.exit_code == 1
    assert "nothing matched" in result.output.lower()
