"""The stand-in answers the real Hugging Face client the way the design says Artifactory does.

These tests drive the installed ``huggingface_hub`` library (what ``jf hf upload`` wraps) against
the stand-in (rules BR1.1 to BR1.9, BR1.14 to BR1.16; requirements FR7.1, FR7.2).
"""

import hashlib
import json

import httpx
import pytest
from huggingface_hub import HfApi, snapshot_download
from huggingface_hub.errors import HfHubHTTPError, RepositoryNotFoundError

REV = "0123456789abcdef0123456789abcdef01234567"
REPO = "acme/tiny-model"


def make_folder(tmp_path, big=False):
    folder = tmp_path / "model"
    folder.mkdir()
    (folder / "config.json").write_bytes(json.dumps({"hidden": 8}).encode())
    (folder / "README.md").write_bytes(b"# Tiny\n")  # bytes: no CRLF change on Windows
    (folder / "sub").mkdir()
    (folder / "sub" / "tokenizer.json").write_bytes(b"{}")
    weights = b"W" * (4096 if not big else 3 * 1024 * 1024)
    (folder / "model.safetensors").write_bytes(weights)
    return folder, weights


def file_of(stand_in, path):
    return next(f for f in stand_in.version_files(REPO, REV) if f.path == path)


def upload(api, folder, repo=REPO, revision=REV):
    api.create_repo(repo, exist_ok=True)
    return api.upload_folder(repo_id=repo, folder_path=str(folder), revision=revision)


def test_upload_then_list_and_download_round_trip(api, stand_in, tmp_path):
    folder, weights = make_folder(tmp_path)
    info = upload(api, folder)
    assert info.oid == REV
    files = sorted(api.list_repo_files(REPO, revision=REV))
    assert files == ["README.md", "config.json", "model.safetensors", "sub/tokenizer.json"]
    out = snapshot_download(
        REPO,
        revision=REV,
        endpoint=stand_in.hf_endpoint,
        token=stand_in.token,
        cache_dir=str(tmp_path / "cache"),
    )
    assert (tmp_path / "cache").exists()
    from pathlib import Path

    assert (Path(out) / "model.safetensors").read_bytes() == weights
    assert (Path(out) / "sub" / "tokenizer.json").read_text() == "{}"


def test_a_large_file_goes_through_the_large_file_batch(api, stand_in, tmp_path):
    folder, weights = make_folder(tmp_path, big=True)
    upload(api, folder)
    paths = [c["path"] for c in stand_in.calls]
    assert any("info/lfs/objects/batch" in p for p in paths)
    entry = file_of(stand_in, "model.safetensors")
    assert entry.sha256 == hashlib.sha256(weights).hexdigest()
    assert entry.size == len(weights)


def test_a_version_is_invisible_until_its_commit(api, stand_in, tmp_path):
    folder, _ = make_folder(tmp_path)
    api.create_repo(REPO, exist_ok=True)
    stand_in.add_switch("server-error", scope="commit", times=1)
    with pytest.raises(HfHubHTTPError):
        api.upload_folder(repo_id=REPO, folder_path=str(folder), revision=REV)
    with pytest.raises((RepositoryNotFoundError, HfHubHTTPError)):
        api.list_repo_files(REPO, revision=REV)
    assert stand_in.version_state(REPO, REV) in (None, "partial")
    # the repeat finds it absent and now succeeds
    info = api.upload_folder(repo_id=REPO, folder_path=str(folder), revision=REV)
    assert info.oid == REV
    assert stand_in.version_state(REPO, REV) == "complete"


def test_a_repeat_of_a_complete_version_is_409_and_changes_nothing(api, stand_in, tmp_path):
    folder, _ = make_folder(tmp_path)
    upload(api, folder)
    (folder / "README.md").write_bytes(b"changed")
    with pytest.raises(HfHubHTTPError) as err:
        api.upload_folder(repo_id=REPO, folder_path=str(folder), revision=REV)
    assert err.value.response.status_code == 409
    original = file_of(stand_in, "README.md")
    assert original.sha256 == hashlib.sha256(b"# Tiny\n").hexdigest()


def test_overwrite_replaces_the_files_when_allowed(api, stand_in, tmp_path):
    stand_in.set_overwrite_allowed(True)
    folder, _ = make_folder(tmp_path)
    upload(api, folder)
    (folder / "README.md").write_bytes(b"changed")
    api.upload_folder(repo_id=REPO, folder_path=str(folder), revision=REV)
    readme = file_of(stand_in, "README.md")
    assert readme.sha256 == hashlib.sha256(b"changed").hexdigest()


def test_a_wrong_token_is_401(stand_in, tmp_path):
    bad = HfApi(endpoint=stand_in.hf_endpoint, token="nope")
    with pytest.raises(HfHubHTTPError) as err:
        bad.create_repo(REPO)
    assert err.value.response.status_code == 401


def test_no_write_permission_is_403_on_changing_calls_but_reads_work(api, stand_in, tmp_path):
    folder, _ = make_folder(tmp_path)
    upload(api, folder)
    stand_in.set_write_allowed(False)
    with pytest.raises(HfHubHTTPError) as err:
        api.upload_folder(repo_id=REPO, folder_path=str(folder), revision="b" * 40)
    assert err.value.response.status_code == 403
    assert "README.md" in api.list_repo_files(REPO, revision=REV)


@pytest.mark.parametrize("org", ["-acme", "ac--me", "12345", "acme-"])
def test_bad_names_are_refused_with_400_and_nothing_is_stored(stand_in, org):
    # sent directly: the real client already refuses some of these names before sending them
    r = httpx.post(
        f"{stand_in.hf_endpoint}/api/repos/create",
        json={"name": "model", "organization": org},
        headers={"Authorization": f"Bearer {stand_in.token}"},
    )
    assert r.status_code == 400 and "organisation" in r.json()["message"]
    assert stand_in.repositories() == []


def test_a_bad_revision_name_is_refused(api, stand_in, tmp_path):
    folder, _ = make_folder(tmp_path)
    api.create_repo(REPO, exist_ok=True)
    with pytest.raises(HfHubHTTPError) as err:
        api.upload_folder(repo_id=REPO, folder_path=str(folder), revision="bad_rev")
    assert err.value.response.status_code == 400


def test_a_named_revision_is_mapped_to_a_commit_hash(api, stand_in, tmp_path):
    folder, _ = make_folder(tmp_path)
    api.create_repo(REPO, exist_ok=True)
    info = api.upload_folder(repo_id=REPO, folder_path=str(folder), revision="main")
    assert len(info.oid) == 40
    assert sorted(api.list_repo_files(REPO, revision="main")) == sorted(
        api.list_repo_files(REPO, revision=info.oid)
    )


def test_two_uploads_to_different_versions_do_not_mix(api, stand_in, tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    folder, _ = make_folder(tmp_path)
    api.create_repo(REPO, exist_ok=True)
    revs = ["1" * 40, "2" * 40, "3" * 40, "4" * 40]

    def go(rev):
        return api.upload_folder(repo_id=REPO, folder_path=str(folder), revision=rev).oid

    with ThreadPoolExecutor(4) as pool:
        assert sorted(pool.map(go, revs)) == sorted(revs)
    for rev in revs:
        assert len(stand_in.version_files(REPO, rev)) == 4


def test_the_storage_listing_gives_paths_sizes_and_checksums_in_the_flat_layout(
    api, stand_in, tmp_path
):
    folder, _ = make_folder(tmp_path)
    upload(api, folder)
    listing = stand_in.storage_list(REPO, REV)
    by_path = {f["uri"].lstrip("/"): f for f in listing["files"]}
    assert f"acme/tiny-model/{REV}/config.json" in by_path
    entry = by_path[f"acme/tiny-model/{REV}/config.json"]
    assert entry["sha256"] == hashlib.sha256(json.dumps({"hidden": 8}).encode()).hexdigest()
    assert entry["size"] == len(json.dumps({"hidden": 8}))


def test_the_nested_layout_lists_different_paths(tmp_path):
    from modelhub_stand_in.server import StandIn

    with StandIn(token="t-1", layout="nested", workdir=tmp_path / "w") as s:
        api = HfApi(endpoint=s.hf_endpoint, token=s.token)
        folder, _ = make_folder(tmp_path)
        upload(api, folder)
        uris = [f["uri"] for f in s.storage_list(REPO, REV)["files"]]
        assert f"/acme/tiny-model/revisions/{REV}/files/config.json" in uris


def test_deleting_a_version_removes_its_files_and_a_second_delete_is_404(api, stand_in, tmp_path):
    folder, _ = make_folder(tmp_path)
    upload(api, folder)
    assert stand_in.delete_version(REPO, REV) == 204
    assert stand_in.version_state(REPO, REV) is None
    assert stand_in.delete_version(REPO, REV) == 404
    with pytest.raises((RepositoryNotFoundError, HfHubHTTPError)):
        api.list_repo_files(REPO, revision=REV)


def test_a_delete_needs_write_permission(api, stand_in, tmp_path):
    folder, _ = make_folder(tmp_path)
    upload(api, folder)
    stand_in.set_write_allowed(False)
    assert stand_in.delete_version(REPO, REV) == 403
    assert stand_in.version_state(REPO, REV) == "complete"


def test_large_files_are_virtual_when_over_the_keep_limit_and_fetch_is_501(tmp_path):
    from modelhub_stand_in.server import StandIn

    with StandIn(token="t-2", keep_limit_bytes=100, workdir=tmp_path / "w") as s:
        api = HfApi(endpoint=s.hf_endpoint, token=s.token)
        folder, weights = make_folder(tmp_path)
        upload(api, folder)
        files = {f.path: f for f in s.version_files(REPO, REV)}
        assert files["model.safetensors"].mode == "virtual"
        assert files["model.safetensors"].sha256 == hashlib.sha256(weights).hexdigest()
        assert files["README.md"].mode == "kept"
        url = f"{s.hf_endpoint}/{REPO}/resolve/{REV}/model.safetensors"
        r = httpx.get(url, headers={"Authorization": f"Bearer {s.token}"})
        assert r.status_code == 501 and r.json()["code"] == "content_not_kept"


def test_a_path_marked_keep_is_served_even_above_the_limit(tmp_path):
    from modelhub_stand_in.server import StandIn

    with StandIn(token="t-3", keep_limit_bytes=100, workdir=tmp_path / "w") as s:
        s.mark_keep("model.safetensors")
        api = HfApi(endpoint=s.hf_endpoint, token=s.token)
        folder, weights = make_folder(tmp_path)
        upload(api, folder)
        url = f"{s.hf_endpoint}/{REPO}/resolve/{REV}/model.safetensors"
        r = httpx.get(url, headers={"Authorization": f"Bearer {s.token}"})
        assert r.status_code == 200 and r.content == weights


def test_a_wrong_checksum_for_a_large_object_is_422(stand_in):
    h = {"Authorization": f"Bearer {stand_in.token}"}
    oid = hashlib.sha256(b"declared").hexdigest()
    base = stand_in.hf_endpoint
    httpx.post(
        f"{base}/api/repos/create", json={"name": "tiny-model", "organization": "acme"}, headers=h
    )
    r = httpx.post(
        f"{base}/acme/tiny-model.git/info/lfs/objects/batch",
        json={
            "operation": "upload",
            "transfers": ["basic"],
            "objects": [{"oid": oid, "size": 8}],
            "hash_algo": "sha256",
        },
        headers=h,
    )
    action = r.json()["objects"][0]["actions"]["upload"]
    put = httpx.put(action["href"], content=b"differen", headers={**h, **action.get("header", {})})
    assert put.status_code == 422


def test_unknown_calls_are_404_not_imitated_and_recorded(stand_in):
    r = httpx.get(
        f"{stand_in.hf_endpoint}/api/spaces/x/y",
        headers={"Authorization": f"Bearer {stand_in.token}"},
    )
    assert r.status_code == 404 and r.json()["code"] == "not_imitated"
    assert stand_in.calls[-1]["status"] == 404


def test_the_call_record_holds_no_token_and_no_body(api, stand_in, tmp_path):
    folder, _ = make_folder(tmp_path)
    upload(api, folder)
    text = json.dumps(stand_in.calls)
    assert stand_in.token not in text
    assert "hidden" not in text
    first = stand_in.calls[0]
    assert set(first) >= {"sequence", "method", "path", "status", "received_at"}
    assert [c["sequence"] for c in stand_in.calls] == list(range(1, len(stand_in.calls) + 1))


def test_an_upload_path_that_escapes_the_version_folder_is_refused(stand_in):
    h = {"Authorization": f"Bearer {stand_in.token}"}
    base = stand_in.hf_endpoint
    httpx.post(
        f"{base}/api/repos/create", json={"name": "tiny-model", "organization": "acme"}, headers=h
    )
    body = "\n".join(
        [
            json.dumps({"key": "header", "value": {"summary": "x"}}),
            json.dumps(
                {
                    "key": "file",
                    "value": {"path": "../evil.txt", "encoding": "base64", "content": "eA=="},
                }
            ),
        ]
    )
    r = httpx.post(
        f"{base}/api/models/acme/tiny-model/commit/{REV}",
        content=body,
        headers={**h, "Content-Type": "application/x-ndjson"},
    )
    assert r.status_code == 400
    assert stand_in.version_state(REPO, REV) is None


def test_a_half_version_failure_leaves_the_version_partial_and_invisible(api, stand_in, tmp_path):
    folder, _ = make_folder(tmp_path)
    api.create_repo(REPO, exist_ok=True)
    stand_in.add_switch("half-version", scope="commit")
    with pytest.raises(HfHubHTTPError):
        api.upload_folder(repo_id=REPO, folder_path=str(folder), revision=REV)
    assert stand_in.version_state(REPO, REV) == "partial"
    assert 0 < len(stand_in.version_files(REPO, REV)) < 4
    with pytest.raises((RepositoryNotFoundError, HfHubHTTPError)):
        api.list_repo_files(REPO, revision=REV)
    assert stand_in.storage_list_status(REPO, REV) == 404
    info = api.upload_folder(repo_id=REPO, folder_path=str(folder), revision=REV)
    assert info.oid == REV and len(stand_in.version_files(REPO, REV)) == 4


def test_a_cut_fetch_gives_a_short_body(api, stand_in, tmp_path):
    folder, weights = make_folder(tmp_path, big=True)
    upload(api, folder)
    stand_in.add_switch("cut-transfer", scope="fetch")
    url = f"{stand_in.hf_endpoint}/{REPO}/resolve/{REV}/model.safetensors"
    with pytest.raises(httpx.HTTPError):
        r = httpx.get(url, headers={"Authorization": f"Bearer {stand_in.token}"})
        assert len(r.content) < len(weights)
        raise httpx.ReadError("short body")
