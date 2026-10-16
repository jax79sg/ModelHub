"""Sign-in, session and the default-deny rule (BR1.1, BR1.2, BR1.3, BR1.4, BR1.11)."""

from urllib.parse import urlsplit

import pytest
from conftest import BASE, make_portal, sign_in

OPEN = ["/healthz", "/readyz", "/auth/login", "/auth/signed-out", "/static/app.css"]
CLOSED = ["/models", "/", "/account/tokens", "/acme/tiny", "/acme/tiny/readme-asset/abc/x.png"]


@pytest.mark.parametrize("path", CLOSED)
def test_every_page_sends_a_person_without_a_session_to_sign_in(portal, path):
    r = portal.get(path)
    assert r.status_code == 302 and r.headers["location"].startswith("/auth/login")
    assert "acme" not in r.text


def test_open_paths_need_no_session(portal):
    assert portal.get("/healthz").status_code == 200
    assert portal.get("/static/app.css").status_code == 200
    assert portal.get("/auth/signed-out").status_code == 200


def test_the_sign_in_goes_to_keycloak_with_a_proof_key_and_a_state(portal, keycloak):
    r = portal.get("/auth/login?next=/models")
    url = urlsplit(r.headers["location"])
    assert (
        url.path.endswith("/protocol/openid-connect/auth")
        and "code_challenge_method=S256" in url.query
    )
    assert "state=" in url.query and "response_type=code" in url.query
    assert "mh_state" in r.headers["set-cookie"] and "HttpOnly" in r.headers["set-cookie"]


def test_a_full_sign_in_lands_on_the_page_asked_for_and_sets_a_safe_cookie(portal, keycloak):
    r = portal.get("/auth/login?next=/models")
    back = keycloak.authorize(r.headers["location"], username="ada")
    done = portal.get(back.removeprefix(BASE))
    assert done.status_code == 302 and done.headers["location"] == "/models"
    cookie = next(c for c in done.headers.get_list("set-cookie") if c.startswith("mh_session="))
    assert (
        "HttpOnly" in cookie
        and "Secure" in cookie
        and "SameSite=lax" in cookie.replace("Lax", "lax")
    )
    assert portal.get("/models").status_code == 200


def test_the_tokens_never_reach_the_browser(portal, keycloak):
    sign_in(portal, keycloak)
    r = portal.get("/models")
    jar = " ".join(f"{c.name}={c.value}" for c in portal.cookies.jar)
    assert "eyJ" not in jar and "eyJ" not in r.text


def test_a_callback_with_the_wrong_state_or_no_login_cookie_is_refused(portal, keycloak):
    r = portal.get("/auth/login")
    back = keycloak.authorize(r.headers["location"]).removeprefix(BASE)
    bad = back.replace("state=", "state=x")
    assert portal.get(bad).status_code == 400
    portal.cookies.clear()
    assert portal.get(back).status_code == 400
    assert portal.get("/models").status_code == 302


def test_an_open_redirect_is_not_followed(portal, keycloak):
    r = portal.get("/auth/login?next=https://evil.example/")
    done = portal.get(keycloak.authorize(r.headers["location"]).removeprefix(BASE))
    assert done.headers["location"] == "/models"


def test_sign_out_ends_both_sessions_and_needs_the_form_token(signed_in, keycloak):
    from conftest import csrf_of

    assert signed_in.post("/auth/logout", data={}, headers={"Origin": BASE}).status_code == 403
    r = signed_in.post("/auth/logout", data={"_csrf": csrf_of(signed_in)}, headers={"Origin": BASE})
    assert r.status_code == 302 and r.headers["location"] == "/auth/signed-out"
    assert keycloak.logged_out and keycloak.logged_out[0]
    assert signed_in.get("/models").status_code == 302


def test_forged_posts_change_nothing(signed_in):
    from conftest import csrf_of

    token = csrf_of(signed_in)
    other = signed_in.post(
        "/account/tokens",
        data={"name": "x", "_csrf": token},
        headers={"Origin": "https://evil.example"},
    )
    assert other.status_code == 403
    nothing = signed_in.post("/account/tokens", data={"name": "x"}, headers={"Origin": BASE})
    assert nothing.status_code == 403


def test_an_idle_session_ends_after_eight_hours(portal, keycloak, clock):
    sign_in(portal, keycloak)
    clock.advance(hours=7)
    assert portal.get("/models").status_code == 200
    clock.advance(hours=7.9)
    assert portal.get("/models").status_code == 200  # the idle clock restarted at each request
    clock.advance(hours=8.1)
    assert portal.get("/models").status_code == 302


def test_the_access_token_is_refreshed_before_it_expires(portal, keycloak, clock):
    keycloak.access_lifetime = 100
    sign_in(portal, keycloak)
    before = len([c for c in keycloak.calls if c[1].endswith("/token")])
    clock.advance(seconds=90)
    assert portal.get("/models").status_code == 200
    assert len([c for c in keycloak.calls if c[1].endswith("/token")]) == before + 1


def test_a_refused_refresh_ends_the_session(portal, keycloak, clock):
    keycloak.access_lifetime = 100
    sign_in(portal, keycloak)
    keycloak.refuse_refresh = True
    clock.advance(seconds=95)
    assert portal.get("/models").status_code == 302


def test_when_keycloak_is_down_signed_in_people_continue_and_new_sign_ins_say_so(
    portal, keycloak, clock
):
    keycloak.access_lifetime = 1000
    sign_in(portal, keycloak)
    keycloak.down = True
    clock.advance(seconds=100)  # the access token is still valid
    assert portal.get("/models").status_code == 200
    fresh = make_portal(keycloak, portal.app.state.catalog_http, clock)
    r = fresh.get("/auth/login")
    assert r.status_code == 503 and "sign-in" in r.text.lower()


def test_when_the_token_expires_and_keycloak_is_down_the_person_is_asked_to_sign_in_again(
    portal, keycloak, clock
):
    keycloak.access_lifetime = 100
    sign_in(portal, keycloak)
    keycloak.down = True
    clock.advance(seconds=150)
    r = portal.get("/models")
    assert r.status_code == 401 and "sign in again" in r.text.lower()


def test_the_security_headers_are_on_every_answer(portal):
    r = portal.get("/healthz")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'none'" in r.headers["content-security-policy"]
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["x-request-id"]


def test_admin_links_are_shown_only_to_administrators(portal, keycloak):
    sign_in(portal, keycloak, username="ada")
    assert "/admin/retention" not in portal.get("/models").text
    portal.cookies.clear()
    sign_in(portal, keycloak, username="root", admin=True)
    assert "/admin/retention" in portal.get("/models").text
