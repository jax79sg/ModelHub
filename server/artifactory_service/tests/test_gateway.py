"""The only caller of Artifactory (rule BR1.19, BR1.7, BR1.3; C5)."""

import os
import stat
import sys
from pathlib import Path

import pytest
from modelhub_artifactory_service.gateway import (
    Gateway,
    HfUploader,
    JfUploader,
    UploadConflict,
    UploadNetworkError,
    UploadRefused,
)
from modelhub_stand_in.server import StandIn

REV = "0123456789abcdef0123456789abcdef01234567"
MODEL = "acme/tiny-model"
FILES = {
    "config.json": b'{"hidden": 8}',
    "README.md": b"# Tiny\n",
    "sub/tokenizer.json": b"{}",
    "model.safetensors": b"W" * 4096,
}


@pytest.fixture(autouse=True)
def _no_xet(monkeypatch):
    monkeypatch.setenv("HF_HUB_DISABLE_XET", "1")
    monkeypatch.setenv("HF_HUB_DISABLE_TELEMETRY", "1")


@pytest.fixture(params=["flat", "nested"])
def stand_in(request, tmp_path):
    with StandIn(token="svc-token-1", layout=request.param, workdir=tmp_path / "si") as s:
        yield s


def folder(tmp_path, files=FILES):
    root = tmp_path / "model"
    for rel, data in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return root


def expected(files=FILES):
    import hashlib

    return {p: (len(d), hashlib.sha256(d).hexdigest()) for p, d in files.items()}


def gateway(stand_in, **kw):
    return Gateway(stand_in.url, stand_in.repo_key, stand_in.token, **kw)


def upload(stand_in, tmp_path, files=FILES, revision=REV):
    gw = gateway(stand_in)
    gw.uploader.upload(folder(tmp_path, files), MODEL, revision)
    return gw


# --- listing: discover, never build ------------------------------------------------------------
def test_a_complete_version_is_found_and_matches_in_either_layout(stand_in, tmp_path):
    gw = upload(stand_in, tmp_path)
    listing = gw.list_version(MODEL, REV, expected())
    assert listing.state == "complete"
    assert listing.differences == []
    assert set(listing.files) == set(FILES)


def test_a_version_that_is_not_there_is_absent(stand_in):
    listing = gateway(stand_in).list_version(MODEL, REV, expected())
    assert listing.state == "absent" and listing.files == {}


def test_a_changed_file_makes_it_inconsistent_and_names_the_difference(stand_in, tmp_path):
    gw = upload(stand_in, tmp_path, files={**FILES, "config.json": b"changed!"})
    listing = gw.list_version(MODEL, REV, expected())
    assert listing.state == "inconsistent"
    assert any("config.json" in d for d in listing.differences)


def test_a_missing_file_and_an_extra_file_are_named(stand_in, tmp_path):
    files = {k: v for k, v in FILES.items() if k != "README.md"}
    files["extra.txt"] = b"x"
    gw = upload(stand_in, tmp_path, files=files)
    listing = gw.list_version(MODEL, REV, expected())
    text = " ".join(listing.differences)
    assert listing.state == "inconsistent"
    assert "README.md" in text and "extra.txt" in text


def test_another_revision_of_the_same_model_is_not_mistaken_for_this_one(stand_in, tmp_path):
    upload(stand_in, tmp_path, revision="b" * 40)
    assert gateway(stand_in).list_version(MODEL, REV, expected()).state == "absent"


def test_listing_without_expectations_just_reports_what_is_there(stand_in, tmp_path):
    gw = upload(stand_in, tmp_path)
    listing = gw.list_version(MODEL, REV)
    assert listing.state == "present" and len(listing.files) == 4


def test_the_listing_falls_back_to_the_whole_repository_when_the_model_folder_is_not_found(
    tmp_path,
):
    # A layout that does not put <org>/<model> first: only the whole-repository listing finds it.
    with StandIn(token="svc-token-2", workdir=tmp_path / "si") as s:
        gw = Gateway(s.url, s.repo_key, s.token)
        gw.uploader.upload(folder(tmp_path), MODEL, REV)
        original = gw._list_prefix
        calls = []

        def only_whole_repo(prefix):
            calls.append(prefix)
            return None if prefix else original(prefix)

        gw._list_prefix = only_whole_repo
        assert gw.list_version(MODEL, REV, expected()).state == "complete"
        assert calls[-1] == ""


# --- delete ------------------------------------------------------------------------------------
def test_deleting_a_version_removes_its_files_and_a_second_delete_counts_as_gone(
    stand_in, tmp_path
):
    gw = upload(stand_in, tmp_path)
    listing = gw.list_version(MODEL, REV, expected())
    assert gw.delete_version(listing) == "deleted"
    assert gw.list_version(MODEL, REV, expected()).state == "absent"
    assert gw.delete_version(listing) == "gone"


def test_a_refused_delete_is_reported(stand_in, tmp_path):
    gw = upload(stand_in, tmp_path)
    listing = gw.list_version(MODEL, REV, expected())
    stand_in.set_write_allowed(False)
    with pytest.raises(UploadRefused):
        gw.delete_version(listing)
    assert gw.list_version(MODEL, REV, expected()).state == "complete"


# --- upload through the Hugging Face client ----------------------------------------------------
def test_the_hf_uploader_uploads_and_a_repeat_is_a_conflict(stand_in, tmp_path):
    gw = gateway(stand_in)
    assert isinstance(gw.uploader, HfUploader)
    gw.uploader.upload(folder(tmp_path), MODEL, REV)
    with pytest.raises(UploadConflict):
        gw.uploader.upload(folder(tmp_path / "again"), MODEL, REV)


def test_a_wrong_token_is_a_refusal_not_a_conflict(stand_in, tmp_path):
    gw = Gateway(stand_in.url, stand_in.repo_key, "wrong")
    with pytest.raises(UploadRefused):
        gw.uploader.upload(folder(tmp_path), MODEL, REV)


def test_a_bad_name_is_a_refusal(stand_in, tmp_path):
    with pytest.raises(UploadRefused):
        gateway(stand_in).uploader.upload(folder(tmp_path), "-bad/model", REV)


def test_a_server_error_is_a_network_class_error_so_it_can_be_retried(stand_in, tmp_path):
    stand_in.add_switch("server-error", scope="commit", sticky=True)
    with pytest.raises(UploadNetworkError):
        gateway(stand_in).uploader.upload(folder(tmp_path), MODEL, REV)


def test_an_unreachable_server_is_a_network_class_error(tmp_path):
    gw = Gateway("http://127.0.0.1:9", "models-hf", "t")
    with pytest.raises(UploadNetworkError):
        gw.uploader.upload(folder(tmp_path), MODEL, REV)


def test_listing_an_unreachable_server_raises_a_network_error():
    from modelhub_artifactory_service.gateway import ArtifactoryUnreachable

    with pytest.raises(ArtifactoryUnreachable):
        Gateway("http://127.0.0.1:9", "models-hf", "t").list_version(MODEL, REV)


# --- the JFrog CLI uploader --------------------------------------------------------------------
def make_fake_jf(tmp_path, exit_code=0, stderr=""):
    script = tmp_path / "jf"
    log = tmp_path / "jf-call.json"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        f"open({str(log)!r}, 'w').write(json.dumps({{'argv': sys.argv[1:], "
        "'env': {k: v for k, v in os.environ.items() if k.startswith(('HF_', 'JFROG', 'CI'))}}))\n"
        f"sys.stderr.write({stderr!r})\n"
        f"sys.exit({exit_code})\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script, log


def test_the_jf_uploader_runs_jf_hf_upload_with_the_token_in_the_environment_only(tmp_path):
    import json

    script, log = make_fake_jf(tmp_path)
    up = JfUploader(
        "https://art.example",
        "hf-local",
        "super-secret-token-value",
        jf_path=str(script),
    )
    up.upload(folder(tmp_path), MODEL, REV)
    call = json.loads(log.read_text())
    assert call["argv"][:2] == ["hf", "upload"]
    assert call["argv"][3] == MODEL
    assert f"--revision={REV}" in call["argv"] and "--repo-key=hf-local" in call["argv"]
    assert "--repo-type=model" in call["argv"]
    assert "super-secret-token-value" not in " ".join(call["argv"])
    assert call["env"]["HF_TOKEN"] == "super-secret-token-value"
    assert (
        call["env"]["HF_ENDPOINT"] == "https://art.example/artifactory/api/huggingfaceml/hf-local"
    )
    assert call["env"]["JFROG_CLI_AVOID_NEW_VERSION_WARNING"] == "true"
    assert call["env"]["JFROG_CLI_REPORT_USAGE"] == "false"


def test_the_jf_uploader_never_overwrites_so_it_passes_no_overwrite_option(tmp_path):
    import json

    script, log = make_fake_jf(tmp_path)
    JfUploader("https://a", "r", "t", jf_path=str(script)).upload(folder(tmp_path), MODEL, REV)
    assert not any(
        "overwrite" in a.lower() or "force" in a.lower()
        for a in json.loads(log.read_text())["argv"]
    )


@pytest.mark.parametrize(
    "stderr,error",
    [
        ("HfHubHTTPError: 409 Client Error: Conflict for url", UploadConflict),
        ("409 Conflict", UploadConflict),
        ("ConnectionError: Max retries exceeded", UploadNetworkError),
        ("Read timed out", UploadNetworkError),
        ("503 Server Error: Service Unavailable", UploadNetworkError),
        ("401 Client Error: Unauthorized", UploadRefused),
        ("something odd", UploadRefused),
    ],
)
def test_the_jf_uploaders_failures_are_classified_from_its_error_text(tmp_path, stderr, error):
    script, _ = make_fake_jf(tmp_path, exit_code=1, stderr=stderr)
    up = JfUploader("https://a", "r", "t", jf_path=str(script))
    with pytest.raises(error):
        up.upload(folder(tmp_path), MODEL, REV)


def test_a_refusal_never_carries_the_credential_or_raw_tool_output(tmp_path):
    script, _ = make_fake_jf(
        tmp_path, exit_code=1, stderr="auth failed with token super-secret-xyz"
    )
    up = JfUploader("https://a", "r", "super-secret-xyz", jf_path=str(script))
    with pytest.raises(UploadRefused) as err:
        up.upload(folder(tmp_path), MODEL, REV)
    assert "super-secret-xyz" not in str(err.value)
    assert "super-secret-xyz" not in repr(err.value.__dict__)


def test_a_missing_jf_binary_is_a_refusal_with_a_plain_message(tmp_path):
    up = JfUploader("https://a", "r", "t", jf_path=str(tmp_path / "no-such-jf"))
    with pytest.raises(UploadRefused) as err:
        up.upload(folder(tmp_path), MODEL, REV)
    assert "JFrog CLI" in str(err.value)


_ = (os, Path)
