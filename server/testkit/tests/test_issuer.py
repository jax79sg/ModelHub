"""The fake Keycloak issuer must make tokens that a real verifier can check (BQ3)."""

import jwt
import pytest
from modelhub_testkit.issuer import FakeIssuer


@pytest.fixture
def issuer():
    return FakeIssuer()


def _decode(token, issuer, **kw):
    key = jwt.PyJWKSet.from_dict(issuer.jwks()).keys[0].key
    return jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience=kw.get("audience", issuer.audience),
        issuer=issuer.issuer,
    )


def test_valid_token_verifies_and_carries_the_claims(issuer):
    token = issuer.token(sub="u1", username="ada")
    claims = _decode(token, issuer)
    assert claims["sub"] == "u1"
    assert claims["preferred_username"] == "ada"
    assert claims["realm_access"]["roles"] == []


def test_admin_token_has_the_admin_role(issuer):
    claims = _decode(issuer.token(admin=True), issuer)
    assert "modelhub-admin" in claims["realm_access"]["roles"]


def test_expired_token_is_refused_by_a_verifier(issuer):
    with pytest.raises(jwt.ExpiredSignatureError):
        _decode(issuer.token(expires_in=-600), issuer)


def test_wrong_audience_is_refused_by_a_verifier(issuer):
    with pytest.raises(jwt.InvalidAudienceError):
        _decode(issuer.token(audience="someone-else"), issuer)


def test_tampered_token_fails_the_signature_check(issuer):
    head, body, sig = issuer.token().split(".")
    forged = ".".join([head, body[:-2] + ("AA" if body[-2:] != "AA" else "BB"), sig])
    with pytest.raises(jwt.InvalidTokenError):
        _decode(forged, issuer)


def test_rotation_adds_a_key_and_keeps_the_old_one_until_dropped(issuer):
    old = issuer.token()
    issuer.rotate()
    new = issuer.token()
    kids = {k["kid"] for k in issuer.jwks()["keys"]}
    assert len(kids) == 2
    assert jwt.get_unverified_header(old)["kid"] != jwt.get_unverified_header(new)["kid"]
    issuer.drop_old_keys()
    assert len(issuer.jwks()["keys"]) == 1


def test_a_token_signed_by_an_unknown_key_has_an_unknown_kid(issuer):
    other = FakeIssuer()
    kid = jwt.get_unverified_header(other.token())["kid"]
    assert kid not in {k["kid"] for k in issuer.jwks()["keys"]}


def test_shared_secret_token_is_available_for_algorithm_tests(issuer):
    token = issuer.hs256_token()
    assert jwt.get_unverified_header(token)["alg"] == "HS256"


def test_service_token_names_the_service_client(issuer):
    claims = _decode(issuer.service_token(), issuer)
    assert claims["azp"] == "modelhub-artifactory-service"
