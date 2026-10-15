"""Logs are JSON lines and nothing secret is in them (rules BR1.8, BR1.9)."""

import io
import json
import logging
import uuid

import pytest
from modelhub_common.logs import JsonFormatter, configure_logging, valid_request_id
from modelhub_common.secrets import Secret

V1 = "v" + uuid.uuid4().hex[:12]
V2 = "v" + uuid.uuid4().hex[:12]
V3 = "v" + uuid.uuid4().hex[:12]


@pytest.fixture
def stream():
    return io.StringIO()


def make_logger(stream, secrets=(), level="info"):
    logger = logging.getLogger("modelhub.test." + str(id(stream)))
    logger.handlers.clear()
    logger.propagate = False
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter("catalog", secrets=secrets))
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    return logger


def lines(stream):
    return [json.loads(x) for x in stream.getvalue().splitlines()]


def test_one_json_object_per_line_with_the_contract_fields(stream):
    log = make_logger(stream)
    log.info("hello", extra={"event": "store_ok", "requestId": "r-1", "person": "ada"})
    (line,) = lines(stream)
    assert line["service"] == "catalog" and line["level"] == "info"
    assert line["event"] == "store_ok" and line["message"] == "hello"
    assert line["requestId"] == "r-1" and line["person"] == "ada"
    assert line["ts"].endswith("Z")


def test_fields_that_look_secret_are_redacted_whatever_the_case(stream):
    log = make_logger(stream)
    log.info(
        "x",
        extra={
            "event": "e",
            "Token": "abc",
            "db_password": "p",
            "Authorization": "Bearer z",
            "my_secret_thing": "s",
            "pepper_x": "q",
            "Cookie": "c",
        },
    )
    (line,) = lines(stream)
    for key in ("Token", "db_password", "Authorization", "my_secret_thing", "pepper_x", "Cookie"):
        assert line[key] == "[redacted]"


def test_a_loaded_secret_value_inside_text_is_masked(stream):
    secret = Secret("database_password", V1)
    log = make_logger(stream, secrets=[secret])
    log.error("connect failed for postgres://u:" + V1 + "@db/x", extra={"event": "db"})
    out = stream.getvalue()
    assert V1 not in out
    assert "[redacted]" in out


def test_a_secret_value_in_an_extra_text_field_is_masked(stream):
    secret = Secret("artifactory_token", V2)
    log = make_logger(stream, secrets=[secret])
    log.info("x", extra={"event": "e", "detail": "got " + V2 + " back"})
    assert V2 not in stream.getvalue()


def test_levels_below_the_configured_level_are_dropped(stream):
    log = make_logger(stream, level="warning")
    log.info("quiet", extra={"event": "e"})
    log.warning("loud", extra={"event": "e"})
    assert [x["message"] for x in lines(stream)] == ["loud"]


def test_an_exception_is_logged_without_leaking_a_secret(stream):
    secret = Secret("database_password", V3)
    log = make_logger(stream, secrets=[secret])
    try:
        raise RuntimeError("bad " + V3)
    except RuntimeError:
        log.exception("failed", extra={"event": "e"})
    assert V3 not in stream.getvalue()


def test_configure_logging_writes_to_standard_output(capsys):
    configure_logging("portal", level="info")
    logging.getLogger("modelhub.x").info("hi", extra={"event": "e"})
    out = capsys.readouterr().out
    assert json.loads(out.splitlines()[-1])["service"] == "portal"


@pytest.mark.parametrize("value", ["abc-123_X", "a" * 64, "1"])
def test_good_request_ids_are_kept(value):
    assert valid_request_id(value)


@pytest.mark.parametrize("value", ["", "a" * 65, "has space", "bad/slash", "new\nline", None])
def test_bad_request_ids_are_refused(value):
    assert not valid_request_id(value)
