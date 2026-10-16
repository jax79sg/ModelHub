"""The retention and trusted-key screens (BR1.4, BR1.11, BR1.13, BR1.14)."""

import pytest
from conftest import BASE, make_portal, sign_in

C1 = "1" * 40
POST = {"Origin": BASE}


def csrf(client, path="/admin/retention"):
    html = client.get(path).text
    marker = 'name="_csrf" value="'
    start = html.index(marker) + len(marker)
    return html[start : html.index('"', start)]


@pytest.fixture
def admin(portal, keycloak):
    sign_in(portal, keycloak, username="root", admin=True)
    return portal


@pytest.fixture
def person(portal, keycloak):
    sign_in(portal, keycloak, username="ada")
    return portal


# --- who may see and do what (BR1.4) -----------------------------------------------------------
def test_everyone_reads_the_period_but_only_administrators_see_the_rest(person, fake_service):
    html = person.get("/admin/retention").text
    assert "365 days" in html and "acme/old" not in html and "Keep" not in html
    assert ("GET", "/v1/retention/due") not in fake_service.calls


def test_the_keys_screen_and_every_action_need_an_administrator(person, fake_service):
    token = csrf(person)
    assert person.get("/admin/keys").status_code == 403
    for method, path, data in (
        ("post", "/admin/retention/period", {"days": "30"}),
        ("post", "/admin/retention/keep", {"model": "acme/old", "commit": C1}),
        ("post", "/admin/retention/remove", {"model": "acme/old", "commit": C1}),
        ("post", "/admin/keys", {"public_key": "x", "fingerprint": "y", "name": "z"}),
        ("post", "/admin/keys/k1/remove", {}),
    ):
        r = getattr(person, method)(path, data={**data, "_csrf": token}, headers=POST)
        assert r.status_code == 403, path
        assert "administrator" in r.text.lower()
    assert [c for c in fake_service.calls if c[0] in ("POST", "PUT", "DELETE")] == []


def test_the_admin_links_are_not_shown_to_other_people(person):
    assert "/admin/keys" not in person.get("/models").text


# --- retention (BR1.13) ------------------------------------------------------------------------
def test_an_administrator_sees_the_period_the_due_versions_and_past_decisions(admin, fake_service):
    html = admin.get("/admin/retention").text
    assert "365 days" in html and "acme/old" in html and "800" in html
    assert "Keep" in html and "Remove" in html


def test_the_period_can_be_changed_and_a_bad_one_is_explained(admin, fake_service):
    token = csrf(admin)
    ok = admin.post("/admin/retention/period", data={"days": "30", "_csrf": token}, headers=POST)
    assert ok.status_code == 303 and fake_service.period == 30
    bad = admin.post("/admin/retention/period", data={"days": "0", "_csrf": token}, headers=POST)
    assert bad.status_code == 422 and "1 to 3650" in bad.text and fake_service.period == 30
    words = admin.post(
        "/admin/retention/period", data={"days": "abc", "_csrf": token}, headers=POST
    )
    assert words.status_code == 422


def test_keep_restarts_the_age_and_shows_the_decision(admin, fake_service):
    token = csrf(admin)
    r = admin.post(
        "/admin/retention/keep",
        data={"model": "acme/old", "commit": C1, "_csrf": token},
        headers=POST,
    )
    assert r.status_code == 303
    assert ("POST", "/v1/retention/decisions") in fake_service.calls
    assert "keep" in admin.get("/admin/retention").text.lower()


def test_remove_asks_first_and_names_what_will_be_lost(admin, fake_service):
    page = admin.get(f"/admin/retention/remove?model=acme/old&commit={C1}")
    assert "Remove acme/old" in page.text and "cannot be undone" in page.text
    assert not [c for c in fake_service.calls if c == ("POST", "/v1/retention/decisions")]


def test_remove_done_failed_and_files_deleted_but_not_marked(admin, fake_service):
    token = csrf(admin)
    data = {"model": "acme/old", "commit": C1, "_csrf": token}
    done = admin.post("/admin/retention/remove", data=data, headers=POST)
    assert done.status_code == 200 and "removed" in done.text.lower()
    fake_service.remove_outcome = {"outcome": "removal_failed", "message": "Artifactory refused."}
    failed = admin.post("/admin/retention/remove", data=data, headers=POST)
    assert "Artifactory refused" in failed.text and "Try again" in failed.text
    assert "stays listed" in failed.text.lower() or "still listed" in failed.text.lower()


def test_a_second_administrator_sees_already_decided(admin, fake_service):
    fake_service.decide_status = 409
    token = csrf(admin)
    r = admin.post(
        "/admin/retention/remove",
        data={"model": "acme/old", "commit": C1, "_csrf": token},
        headers=POST,
    )
    assert r.status_code == 409 and "already" in r.text.lower()


def test_there_is_no_bulk_action(admin):
    for path in ("/admin/retention/remove-all", "/admin/retention/keep-all"):
        assert admin.post(path, data={}, headers=POST).status_code in (404, 405)


# --- trusted keys (BR1.14) ---------------------------------------------------------------------
def test_keys_are_listed_and_a_matching_fingerprint_adds_one(admin, fake_service):
    assert "release key" in admin.get("/admin/keys").text
    token = csrf(admin, "/admin/keys")
    r = admin.post(
        "/admin/keys",
        data={"public_key": "{}", "fingerprint": "cccc-dddd", "name": "second", "_csrf": token},
        headers=POST,
    )
    assert r.status_code == 303 and any(k["name"] == "second" for k in fake_service.keys)


def test_a_fingerprint_mismatch_is_shown_plainly_and_nothing_is_added(admin, fake_service):
    fake_service.add_error = (
        422,
        {
            "code": "fingerprint_mismatch",
            "message": "the typed fingerprint does not match this key",
        },
    )
    token = csrf(admin, "/admin/keys")
    r = admin.post(
        "/admin/keys",
        data={"public_key": "{}", "fingerprint": "no", "name": "second", "_csrf": token},
        headers=POST,
    )
    assert r.status_code == 422 and "does not match" in r.text and len(fake_service.keys) == 1


def test_stopping_trusting_asks_first_then_does_it(admin, fake_service):
    assert "Stop trusting" in admin.get("/admin/keys/k1/remove").text
    token = csrf(admin, "/admin/keys")
    r = admin.post("/admin/keys/k1/remove", data={"_csrf": token}, headers=POST)
    assert r.status_code == 303 and fake_service.keys[0]["status"] == "revoked"


# --- the service being down (BR1.11) -----------------------------------------------------------
def test_when_the_service_is_down_the_screens_say_so(admin, fake_service):
    fake_service.down = True
    for path in ("/admin/retention", "/admin/keys"):
        r = admin.get(path)
        assert r.status_code == 503 and "retention service cannot be reached" in r.text
        assert "Try again" in r.text


def test_the_persons_own_token_is_what_the_service_receives(admin, fake_service):
    admin.get("/admin/retention")
    assert fake_service.auth and all(a.startswith("Bearer eyJ") for a in fake_service.auth)


def test_without_a_service_configured_the_screens_say_so(keycloak, catalog_http, clock):
    bare = make_portal(keycloak, catalog_http, clock)
    sign_in(bare, keycloak, username="root", admin=True)
    assert bare.get("/admin/retention").status_code == 503
