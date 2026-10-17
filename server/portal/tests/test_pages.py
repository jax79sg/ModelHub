"""The models list, the model page and the token page (BR1.5, BR1.6, BR1.8, BR1.10, BR1.11, BR1.12)."""

import re

import pytest
from conftest import BASE, csrf_of, sign_in
from seed import PNG, put

C1 = "1" * 40
C2 = "2" * 40


@pytest.fixture
def issuer(keycloak):
    return keycloak.issuer


@pytest.fixture
def data(catalog_http, issuer):
    put(catalog_http, issuer, "acme/tiny", C1, task="text-generation", downloads=10)
    put(
        catalog_http,
        issuer,
        "acme/other",
        C2,
        task="translation",
        license="apache-2.0",
        downloads=99,
        library="timm",
    )
    return catalog_http


@pytest.fixture
def page(data, signed_in):
    return signed_in


def names(html):
    return re.findall(r'class="model-id">([^<]+)<', html)


# --- the list ----------------------------------------------------------------------------------
def test_the_list_shows_every_model_most_downloaded_first(page):
    assert names(page.get("/models").text) == ["acme/other", "acme/tiny"]


def test_a_filter_is_passed_to_the_catalog_and_the_counts_are_shown(page):
    html = page.get("/models?task=translation").text
    assert names(html) == ["acme/other"]
    assert 'class="chip active"' in html  # the chosen value stays, so it can be taken off again


def test_search_sort_and_licence(page):
    assert names(page.get("/models?search=other").text) == ["acme/other"]
    assert names(page.get("/models?sort=name").text) == ["acme/other", "acme/tiny"]
    assert names(page.get("/models?license=mit").text) == ["acme/tiny"]


def test_an_empty_answer_says_so(page):
    assert "No models match" in page.get("/models?search=zzzzzz").text


def test_a_value_the_catalog_refuses_is_explained_and_the_full_list_is_shown(page):
    html = page.get("/models?sort=bogus").text
    assert 'role="status"' in html and len(names(html)) == 2


def test_null_counts_show_unknown_never_zero(catalog_http, issuer, signed_in):
    put(
        catalog_http,
        issuer,
        "acme/bare",
        C1,
        downloads=None,
        likes=None,
        license=None,
        task=None,
        library=None,
    )
    html = signed_in.get("/models").text
    assert "downloads unknown" in html and "likes unknown" in html and "no licence given" in html


def test_a_removed_version_is_hidden_unless_asked_for(page, data, issuer):
    r = data.post(
        f"/v1/models/acme/tiny/versions/{C1}/removal",
        json={"removedBy": "root"},
        headers={"Authorization": f"Bearer {issuer.service_token()}"},
    )
    assert r.status_code == 200
    assert names(page.get("/models").text) == ["acme/other"]
    assert "acme/tiny" in names(page.get("/models?showRemoved=1").text)


def test_paging_is_30_per_page(catalog_http, issuer, signed_in):
    for n in range(31):
        put(catalog_http, issuer, f"acme/m{n:02d}", f"{n:040x}")
    first = signed_in.get("/models?sort=name").text
    assert len(names(first)) == 30 and "Page 1 of 2" in first
    assert len(names(signed_in.get("/models?sort=name&p=2").text)) == 1


# --- the model page ----------------------------------------------------------------------------
def test_the_model_page_shows_the_card_facts_and_files(page):
    html = page.get("/acme/tiny").text
    assert "<em>tiny</em>" in html and "License: <b>mit</b>" in html
    assert "config.json" in html and "not in store" in html
    assert "<dt>Downloads</dt><dd>10 " in html


def test_unknown_values_are_said_plainly(catalog_http, issuer, signed_in):
    put(
        catalog_http,
        issuer,
        "acme/bare",
        C1,
        license=None,
        downloads=None,
        parameter_count=None,
        documents=[],
    )
    html = signed_in.get("/acme/bare").text
    assert "no licence given" in html and "No README stored" in html and "unknown" in html


def test_a_model_that_was_not_imported_is_a_plain_not_found(page):
    r = page.get("/acme/missing")
    assert r.status_code == 404 and "has not been imported" in r.text


def test_the_revision_can_be_a_ref_name_or_a_short_commit(page):
    assert page.get("/acme/tiny?rev=main").status_code == 200
    assert page.get(f"/acme/tiny?rev={C1[:8]}").status_code == 200
    assert page.get("/acme/tiny?rev=nope").status_code == 404
    assert page.get("/acme/tiny?rev=111").status_code == 404  # too short to mean anything


def test_two_versions_are_offered_in_the_revision_menu(catalog_http, issuer, signed_in):
    put(
        catalog_http,
        issuer,
        "acme/tiny",
        C1,
        refs=[{"name": "main", "kind": "branch", "commit": C1}],
    )
    put(
        catalog_http,
        issuer,
        "acme/tiny",
        C2,
        refs=[{"name": "dev", "kind": "branch", "commit": C2}],
    )
    html = signed_in.get("/acme/tiny").text
    assert "?rev=main" in html and "?rev=dev" in html


def test_a_removed_version_has_a_page_and_a_banner(page, data, issuer):
    data.post(
        f"/v1/models/acme/tiny/versions/{C1}/removal",
        json={"removedBy": "root"},
        headers={"Authorization": f"Bearer {issuer.service_token()}"},
    )
    html = page.get("/acme/tiny").text
    assert "This version was removed" in html and "root" in html and "no longer stored" in html


def test_fetch_instructions_hold_the_placeholder_and_no_real_token(page):
    html = page.get("/acme/tiny").text
    assert "jf hf download acme/tiny" in html and "&lt;your-token&gt;" in html
    assert "api/huggingfaceml/hf-local" in html
    assert "mhi_" not in html


def test_there_is_no_route_that_serves_a_model_file(page):
    for path in ("/acme/tiny/resolve/main/config.json", "/acme/tiny/raw/main/config.json"):
        assert page.get(path).status_code in (404, 405)


# --- the card is rendered safely ---------------------------------------------------------------
def test_hostile_card_text_is_made_safe_and_requests_nothing_outside(
    catalog_http, issuer, signed_in
):
    hostile = (
        b'# T\n\n<script>alert(1)</script>\n\n<img src="https://evil.example/x.png" onerror="alert(2)">\n\n'
        b"[click](javascript:alert(3))\n\n![p](https://evil.example/p.png)\n"
    )
    put(
        catalog_http,
        issuer,
        "acme/evil",
        C1,
        documents=[("readme/README.md", hostile, "text/markdown")],
    )
    html = signed_in.get("/acme/evil").text
    assert "<script>alert" not in html and "onerror" not in html
    assert 'href="javascript' not in html and 'src="https://' not in html
    assert 'src="http://' not in html


def test_stored_pictures_are_served_as_data_with_nosniff_and_never_svg(
    catalog_http, issuer, signed_in
):
    docs = [
        ("readme/README.md", b"# T\n\n![pic](assets/a.png)\n", "text/markdown"),
        ("picture/a.png", PNG, "image/png"),
        ("picture/b.svg", b"<svg onload=alert(1)></svg>", "image/svg+xml"),
    ]
    put(catalog_http, issuer, "acme/pics", C1, documents=docs)
    assert f"/acme/pics/readme-asset/{C1}/assets/a.png" in signed_in.get("/acme/pics").text
    ok = signed_in.get(f"/acme/pics/readme-asset/{C1}/assets/a.png")
    assert ok.status_code == 200 and ok.headers["content-type"] == "image/png"
    assert (
        ok.headers["x-content-type-options"] == "nosniff"
        and "sandbox" in ok.headers["content-security-policy"]
    )
    svg = signed_in.get(f"/acme/pics/readme-asset/{C1}/assets/b.svg")
    assert (
        svg.headers["content-type"] == "application/octet-stream"
        and "attachment" in svg.headers["content-disposition"]
    )
    assert signed_in.get(f"/acme/pics/readme-asset/{C1}/assets/none.png").status_code == 404


# --- failures ----------------------------------------------------------------------------------
def test_when_the_catalog_is_down_the_page_says_so_and_shows_no_model(page, data, monkeypatch):
    import httpx

    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(data, "request", boom)
    r = page.get("/models")
    assert (
        r.status_code == 503
        and "model database cannot be reached" in r.text
        and "acme/" not in r.text
    )
    assert "Try again" in r.text


def test_a_catalog_server_error_is_the_same_plain_message(page, data, monkeypatch):
    import httpx

    monkeypatch.setattr(data, "request", lambda *a, **k: httpx.Response(500))
    assert page.get("/acme/tiny").status_code == 503


# --- personal tokens ---------------------------------------------------------------------------
def test_a_token_is_made_shown_once_listed_and_revoked(signed_in, catalog_http):
    token = csrf_of(signed_in)
    r = signed_in.post(
        "/account/tokens", data={"name": "laptop", "_csrf": token}, headers={"Origin": BASE}
    )
    assert r.status_code == 200
    value = re.search(r'id="new-token">(mhi_[^<]+)<', r.text).group(1)
    assert "no-store" in r.headers["cache-control"]
    assert "copy" in r.text.lower() and "only once" in r.text
    listing = signed_in.get("/account/tokens")
    assert value not in listing.text and value[:8] in listing.text and "laptop" in listing.text
    token_id = re.search(r"/account/tokens/([0-9a-f]+)/revoke", listing.text).group(1)
    assert "cannot be undone" in signed_in.get(f"/account/tokens/{token_id}/revoke").text
    done = signed_in.post(
        f"/account/tokens/{token_id}/revoke", data={"_csrf": token}, headers={"Origin": BASE}
    )
    assert done.status_code == 303
    assert "revoked" in signed_in.get("/account/tokens").text


def test_the_token_value_is_never_logged(signed_in, caplog):
    token = csrf_of(signed_in)
    with caplog.at_level("DEBUG"):
        r = signed_in.post(
            "/account/tokens", data={"name": "x1", "_csrf": token}, headers={"Origin": BASE}
        )
    value = re.search(r'id="new-token">(mhi_[^<]+)<', r.text).group(1)
    assert value not in caplog.text


def test_a_bad_token_name_is_explained(signed_in):
    token = csrf_of(signed_in)
    r = signed_in.post(
        "/account/tokens", data={"name": " ", "_csrf": token}, headers={"Origin": BASE}
    )
    assert r.status_code == 422 and "1 to 60" in r.text


def test_a_person_sees_only_their_own_tokens_and_an_administrator_can_see_all(portal, keycloak):
    sign_in(portal, keycloak, username="ada")
    portal.post(
        "/account/tokens", data={"name": "adas", "_csrf": csrf_of(portal)}, headers={"Origin": BASE}
    )
    portal.cookies.clear()
    sign_in(portal, keycloak, username="bob")
    assert "adas" not in portal.get("/account/tokens?all=1").text
    portal.cookies.clear()
    sign_in(portal, keycloak, username="root", admin=True)
    assert "adas" in portal.get("/account/tokens?all=1").text
    assert "adas" not in portal.get("/account/tokens").text


def test_the_list_can_be_filtered_by_who_imported(catalog_http, issuer, signed_in):
    put(catalog_http, issuer, "acme/a", C1)
    html = signed_in.get("/models").text
    assert "Imported by" in html and "ada" in html
    assert names(signed_in.get("/models?importedByName=ada").text) == ["acme/a"]
    assert "No models match" in signed_in.get("/models?importedByName=nobody").text
