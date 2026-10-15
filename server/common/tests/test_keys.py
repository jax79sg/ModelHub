"""The signing-key set: last good keys kept, refresh limited (rule BR1.4, NFR5.7)."""

import pytest
from modelhub_common.keys import KeySet, KeyState


class Fetcher:
    def __init__(self, issuer):
        self.issuer = issuer
        self.calls = 0
        self.fail = False

    def __call__(self):
        self.calls += 1
        if self.fail:
            raise OSError("keycloak unreachable")
        return self.issuer.jwks()


@pytest.fixture
def fetcher(issuer):
    return Fetcher(issuer)


def kid_of(issuer):
    return issuer.jwks()["keys"][-1]["kid"]


def test_starts_empty_and_loads_on_first_fetch(fetcher, issuer, clock):
    keys = KeySet(fetcher, clock=clock)
    assert keys.state is KeyState.EMPTY
    keys.load()
    assert keys.state is KeyState.LOADED
    assert keys.get(kid_of(issuer)) is not None


def test_a_failed_first_fetch_leaves_the_set_empty(fetcher, clock):
    fetcher.fail = True
    keys = KeySet(fetcher, clock=clock)
    keys.load()
    assert keys.state is KeyState.EMPTY


def test_an_unknown_kid_triggers_one_refresh_and_finds_a_rotated_key(fetcher, issuer, clock):
    keys = KeySet(fetcher, clock=clock)
    keys.load()
    issuer.rotate()
    assert keys.get(kid_of(issuer)) is not None
    assert fetcher.calls == 2


def test_refresh_is_limited_to_once_a_minute(fetcher, issuer, clock):
    keys = KeySet(fetcher, clock=clock)
    keys.load()
    for _ in range(5):
        assert keys.get("nope") is None
    assert fetcher.calls == 2
    clock.advance(61)
    assert keys.get("nope") is None
    assert fetcher.calls == 3


def test_a_failed_refresh_keeps_the_keys_already_held_and_marks_stale(fetcher, issuer, clock):
    keys = KeySet(fetcher, clock=clock)
    keys.load()
    good = kid_of(issuer)
    fetcher.fail = True
    assert keys.get("unknown") is None
    assert keys.state is KeyState.STALE
    assert keys.get(good) is not None


def test_a_later_successful_refresh_makes_the_set_loaded_again(fetcher, issuer, clock):
    keys = KeySet(fetcher, clock=clock)
    keys.load()
    fetcher.fail = True
    keys.get("unknown")
    fetcher.fail = False
    clock.advance(61)
    keys.get("unknown")
    assert keys.state is KeyState.LOADED


def test_a_known_kid_never_calls_keycloak(fetcher, issuer, clock):
    keys = KeySet(fetcher, clock=clock)
    keys.load()
    for _ in range(10):
        keys.get(kid_of(issuer))
    assert fetcher.calls == 1


def test_keys_dropped_by_the_issuer_stay_trusted_until_a_refresh_replaces_the_set(
    fetcher, issuer, clock
):
    keys = KeySet(fetcher, clock=clock)
    keys.load()
    old = kid_of(issuer)
    issuer.rotate()
    issuer.drop_old_keys()
    clock.advance(61)
    keys.get("unknown")
    assert keys.get(old) is None
    assert keys.get(kid_of(issuer)) is not None


def test_the_key_algorithm_is_taken_from_the_key_type(fetcher, issuer, clock):
    keys = KeySet(fetcher, clock=clock)
    keys.load()
    assert keys.get(kid_of(issuer)).algorithm == "RS256"
