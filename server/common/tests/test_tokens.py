"""The token check (rules BR1.1, BR1.2, BR1.3; NFR5.1, NFR5.9)."""

import pytest
from modelhub_common.keys import KeySet
from modelhub_common.tokens import Reason, TokenVerifier


@pytest.fixture
def verifier(issuer, clock):
    keys = KeySet(issuer.jwks, clock=clock)
    keys.load()
    return TokenVerifier(keys, issuer=issuer.issuer, audience=issuer.audience)


def test_a_valid_token_gives_the_person(verifier, issuer):
    v = verifier.verify(issuer.token(sub="u9", username="grace"))
    assert v.valid and v.reason is Reason.OK
    assert (v.person_id, v.person_name, v.is_admin) == ("u9", "grace", False)


def test_the_admin_role_makes_an_administrator(verifier, issuer):
    assert verifier.verify(issuer.token(admin=True)).is_admin is True


def test_a_missing_realm_access_claim_is_not_an_administrator(verifier, issuer):
    v = verifier.verify(issuer.token(drop=("realm_access",)))
    assert v.valid and v.is_admin is False


def test_a_look_alike_role_is_not_the_admin_role(verifier, issuer):
    assert verifier.verify(issuer.token(roles=["modelhub-admins", "admin"])).is_admin is False


@pytest.mark.parametrize("token", [None, ""])
def test_no_token_is_missing(verifier, token):
    assert verifier.verify(token).reason is Reason.MISSING


@pytest.mark.parametrize("token", ["abc", "a.b", "a.b.c.d", "not a token at all"])
def test_garbage_is_malformed(verifier, token):
    assert verifier.verify(token).reason is Reason.MALFORMED


def test_a_shared_secret_token_is_a_bad_algorithm(verifier, issuer):
    assert verifier.verify(issuer.hs256_token()).reason is Reason.BAD_ALGORITHM


def test_an_unsigned_token_is_a_bad_algorithm(verifier, issuer):
    import base64
    import json

    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    token = b64({"alg": "none", "typ": "JWT"}) + "." + b64({"sub": "x"}) + "."
    assert verifier.verify(token).reason is Reason.BAD_ALGORITHM


def test_an_unknown_key_id_is_refused(verifier, issuer):
    from modelhub_testkit.issuer import FakeIssuer

    other = FakeIssuer()
    assert verifier.verify(other.token()).reason is Reason.UNKNOWN_KEY


def test_a_tampered_body_fails_the_signature(verifier, issuer):
    head, body, sig = issuer.token().split(".")
    flipped = "A" if body[10] != "A" else "B"
    forged = ".".join([head, body[:10] + flipped + body[11:], sig])
    assert verifier.verify(forged).reason in (Reason.BAD_SIGNATURE, Reason.MALFORMED)


def test_a_signature_from_another_key_with_the_same_kid_fails(verifier, issuer):
    from modelhub_testkit.issuer import FakeIssuer

    other = FakeIssuer()
    other._keys = [(issuer._keys[-1][0], other._keys[-1][1])]
    assert verifier.verify(other.token()).reason is Reason.BAD_SIGNATURE


def test_wrong_issuer_is_refused(verifier, issuer):
    assert (
        verifier.verify(issuer.token(issuer="https://evil/realms/x")).reason is Reason.WRONG_ISSUER
    )


def test_wrong_audience_is_refused(verifier, issuer):
    assert verifier.verify(issuer.token(audience="other")).reason is Reason.WRONG_AUDIENCE


def test_an_audience_list_that_includes_ours_is_accepted(verifier, issuer):
    v = verifier.verify(issuer.token(audience=["account", issuer.audience]))
    assert v.valid


def test_an_expired_token_is_refused(verifier, issuer):
    assert verifier.verify(issuer.token(expires_in=-120)).reason is Reason.EXPIRED


def test_a_token_expired_within_the_allowance_is_accepted(verifier, issuer):
    assert verifier.verify(issuer.token(expires_in=-30)).valid


def test_a_token_not_yet_valid_is_refused(verifier, issuer):
    import time

    nbf = int(time.time()) + 600
    assert verifier.verify(issuer.token(extra={"nbf": nbf})).reason is Reason.NOT_YET_VALID


@pytest.mark.parametrize("claim", ["sub", "preferred_username", "exp"])
def test_a_missing_required_claim_is_refused(verifier, issuer, claim):
    assert verifier.verify(issuer.token(drop=(claim,))).reason is Reason.MISSING_CLAIM


def test_the_client_that_asked_is_reported_for_service_tokens(verifier, issuer):
    v = verifier.verify(issuer.service_token())
    assert v.valid and v.client_id == "modelhub-artifactory-service"


def test_a_person_token_has_no_client_id(verifier, issuer):
    assert verifier.verify(issuer.token()).client_id is None


def test_the_verdict_never_contains_the_token(verifier, issuer):
    token = issuer.token()
    v = verifier.verify(token)
    assert token not in repr(v)


def test_an_empty_key_set_refuses_everything_as_unknown_key(issuer, clock):
    def down():
        raise OSError("down")

    keys = KeySet(down, clock=clock)
    keys.load()
    verifier = TokenVerifier(keys, issuer=issuer.issuer, audience=issuer.audience)
    assert verifier.verify(issuer.token()).reason is Reason.UNKNOWN_KEY
