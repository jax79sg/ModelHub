"""The live and ready checks (rules BR1.10, BR1.11)."""

import time

from modelhub_common.health import HealthCheck, HealthRegistry
from modelhub_common.keys import KeyState


def ok():
    return True


def down():
    raise RuntimeError("secret detail from the database")


def test_all_ok_gives_200_ok():
    reg = HealthRegistry([HealthCheck("database", ok, critical=True)])
    status, body = reg.ready(KeyState.LOADED)
    assert status == 200 and body == {"status": "ok", "checks": {"database": "ok"}}


def test_a_critical_check_down_gives_503_down():
    reg = HealthRegistry([HealthCheck("database", down, critical=True)])
    status, body = reg.ready(KeyState.LOADED)
    assert status == 503 and body["status"] == "down"
    assert body["checks"] == {"database": "down"}


def test_only_a_non_critical_check_down_gives_200_degraded():
    reg = HealthRegistry(
        [HealthCheck("database", ok, critical=True), HealthCheck("keycloak", down, critical=False)]
    )
    status, body = reg.ready(KeyState.LOADED)
    assert status == 200 and body["status"] == "degraded"


def test_an_empty_key_set_makes_the_service_not_ready():
    reg = HealthRegistry([HealthCheck("database", ok, critical=True)])
    status, body = reg.ready(KeyState.EMPTY)
    assert status == 503 and body["status"] == "down"


def test_a_stale_key_set_stays_ready():
    reg = HealthRegistry([HealthCheck("database", ok, critical=True)])
    assert reg.ready(KeyState.STALE)[0] == 200


def test_the_answer_never_carries_a_dependency_message():
    reg = HealthRegistry([HealthCheck("database", down, critical=True)])
    _, body = reg.ready(KeyState.LOADED)
    assert "secret detail" not in str(body)


def test_a_check_is_cached_for_ten_seconds():
    calls = []
    now = [100.0]
    reg = HealthRegistry(
        [HealthCheck("database", lambda: calls.append(1) or True, critical=True)],
        clock=lambda: now[0],
    )
    reg.ready(KeyState.LOADED)
    reg.ready(KeyState.LOADED)
    assert len(calls) == 1
    now[0] += 11
    reg.ready(KeyState.LOADED)
    assert len(calls) == 2


def test_a_check_that_hangs_counts_as_down_after_its_limit():
    reg = HealthRegistry(
        [HealthCheck("database", lambda: time.sleep(2), critical=True, timeout=0.2)]
    )
    start = time.monotonic()
    status, body = reg.ready(KeyState.LOADED)
    assert time.monotonic() - start < 1.5
    assert status == 503 and body["checks"]["database"] == "down"


def test_a_check_returning_false_is_down():
    reg = HealthRegistry([HealthCheck("artifactory", lambda: False, critical=False)])
    assert reg.ready(KeyState.LOADED)[1]["checks"]["artifactory"] == "down"


def test_no_checks_is_ok_once_keys_are_loaded():
    assert HealthRegistry([]).ready(KeyState.LOADED)[0] == 200
