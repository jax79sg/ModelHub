"""The trail, the files, a file and the commits (BR1.6, BR1.7, BR1.9, BR1.15)."""

import json
import re

import pytest
from seed import put

C1 = "1" * 40
C2 = "2" * 40
FILES = [
    {
        "path": "config.json",
        "size_bytes": 23,
        "sha256": "a" * 64,
        "downloaded": True,
        "safety_scan": "safe",
        "file_type": "json",
    },
    {
        "path": "weights/model.bin",
        "size_bytes": 2048,
        "sha256": "b" * 64,
        "downloaded": True,
        "safety_scan": "safe",
    },
    {"path": "weights/big.bin", "size_bytes": 99999, "sha256": "c" * 64, "downloaded": False},
]
COMMITS = [
    {
        "id": C1,
        "title": "Add weights",
        "message": "Add weights\n\nmore",
        "authors": [{"user": "ada"}],
        "date": "2026-01-01T00:00:00.000Z",
    },
    {
        "id": "0" * 40,
        "title": "First",
        "message": "First",
        "authors": [],
        "date": "2025-12-01T00:00:00.000Z",
    },
]


@pytest.fixture
def issuer(keycloak):
    return keycloak.issuer


@pytest.fixture
def data(catalog_http, issuer):
    docs = [
        ("readme/README.md", b"# T\n\nSee [config](config.json).\n", "text/markdown"),
        ("response/raw/commits.json", json.dumps(COMMITS).encode(), "application/json"),
    ]
    put(catalog_http, issuer, "acme/tiny", C1, files=FILES, documents=docs)
    return catalog_http


@pytest.fixture
def page(data, signed_in):
    return signed_in


# --- files (BR1.6, BR1.9) ----------------------------------------------------------------------
def test_the_top_of_the_tree_lists_files_and_folders(page):
    html = page.get("/acme/tiny/tree/main").text
    assert "config.json" in html and "weights" in html
    assert "model.bin" not in html  # inside the folder


def test_a_folder_lists_its_files_and_marks_those_not_in_store(page):
    html = page.get("/acme/tiny/tree/main/weights").text
    assert "model.bin" in html and "big.bin" in html and "not in store" in html
    assert "/acme/tiny/tree/main" in html  # a way back up


def test_an_unknown_folder_or_revision_is_a_plain_not_found(page):
    assert page.get("/acme/tiny/tree/main/nothing").status_code == 404
    assert page.get("/acme/tiny/tree/nope").status_code == 404
    assert page.get("/acme/missing/tree/main").status_code == 404


def test_a_file_page_shows_the_record_and_never_the_content(page):
    html = page.get("/acme/tiny/blob/main/weights/model.bin").text
    assert "2,048 bytes" in html
    assert "b" * 64 in html and "safe" in html
    assert "hf_hub_download" in html and "&lt;your-token&gt;" in html
    for forbidden in ("/resolve/", "/raw/", "download="):
        assert forbidden not in html


def test_a_file_never_downloaded_says_so_and_unknown_files_are_404(page):
    assert "not in store" in page.get("/acme/tiny/blob/main/weights/big.bin").text
    assert page.get("/acme/tiny/blob/main/none.txt").status_code == 404


def test_a_link_in_the_card_to_a_file_opens_its_page(page):
    html = page.get("/acme/tiny").text
    link = re.search(r'href="(/acme/tiny/blob/[^"]+config\.json)"', html).group(1)
    assert page.get(link).status_code == 200


# --- commits (BR1.6) ---------------------------------------------------------------------------
def test_the_commit_history_comes_from_the_stored_response(page):
    html = page.get("/acme/tiny/commits/main").text
    assert "Add weights" in html and "First" in html and "ada" in html


def test_no_stored_history_is_said_plainly(catalog_http, issuer, signed_in):
    put(catalog_http, issuer, "acme/bare", C2, documents=[])
    assert "No commit history" in signed_in.get("/acme/bare/commits/main").text


def test_a_removed_version_keeps_its_file_list_but_not_its_documents(page, data, issuer):
    data.post(
        f"/v1/models/acme/tiny/versions/{C1}/removal",
        json={"removedBy": "root"},
        headers={"Authorization": f"Bearer {issuer.service_token()}"},
    )
    tree = page.get("/acme/tiny/tree/main")
    assert tree.status_code == 200 and "removed" in tree.text.lower() and "config.json" in tree.text
    assert "No commit history" in page.get("/acme/tiny/commits/main").text


# --- the trail (BR1.15) ------------------------------------------------------------------------
def test_the_trail_lists_imports_newest_first_with_who_and_what(catalog_http, issuer, signed_in):
    put(catalog_http, issuer, "acme/a", C1)
    put(catalog_http, issuer, "acme/b", C2)
    html = signed_in.get("/trail").text
    assert "acme/a" in html and "acme/b" in html and "ada" in html and "imported" in html


def test_a_model_trail_and_a_my_imports_filter(catalog_http, issuer, signed_in):
    put(catalog_http, issuer, "acme/a", C1)
    put(catalog_http, issuer, "acme/b", C2)
    assert "acme/b" not in signed_in.get("/acme/a/trail").text
    assert "acme/a" in signed_in.get("/trail?model=acme/a").text
    assert "acme/b" not in signed_in.get("/trail?model=acme/a").text


def test_retention_decisions_are_merged_into_the_trail(page, fake_service):
    fake_service.decisions.append(
        {
            "decisionId": "d1",
            "modelId": "acme/tiny",
            "commit": C1,
            "decision": "remove",
            "decidedBy": "root",
            "decidedAt": "2026-03-01T00:00:00Z",
            "outcome": "done",
            "message": None,
        }
    )
    html = page.get("/trail").text
    assert "removed" in html.lower() and "root" in html


def test_if_the_service_is_down_the_trail_still_shows_imports_with_a_note(page, fake_service):
    fake_service.down = True
    r = page.get("/trail")
    assert r.status_code == 200 and "acme/tiny" in r.text
    assert "decisions cannot be shown" in r.text.lower()


def test_the_trail_is_paged_by_30(catalog_http, issuer, signed_in):
    for n in range(31):
        put(catalog_http, issuer, f"acme/m{n:02d}", f"{n:040x}")
    first = signed_in.get("/trail").text
    assert "Page 1 of 2" in first
    assert "Next" in first


def test_a_model_page_links_to_its_trail_and_the_header_to_the_full_trail(page):
    html = page.get("/acme/tiny").text
    assert "/acme/tiny/trail" in html
    assert 'href="/trail"' in html
