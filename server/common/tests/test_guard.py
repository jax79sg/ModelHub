"""The request guard: default deny, roles, request ids, access log (rules BR1.2, BR1.3, BR1.5, BR1.9)."""

import io
import json
import logging

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from modelhub_common.guard import current_person, install_guard, require_admin, require_client
from modelhub_common.health import HealthCheck, HealthRegistry
from modelhub_common.keys import KeySet
from modelhub_common.logs import JsonFormatter
from modelhub_common.tokens import TokenVerifier


@pytest.fixture
def logbuf():
    stream = io.StringIO()
    logger = logging.getLogger("modelhub")
    old = (list(logger.handlers), logger.level, logger.propagate)
    logger.handlers.clear()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter("test"))
    logger.addHandler(handler)
    logger.setLevel("INFO")
    logger.propagate = False
    yield stream
    logger.handlers[:] = old[0]
    logger.setLevel(old[1])
    logger.propagate = old[2]


@pytest.fixture
def client(issuer, logbuf):
    keys = KeySet(issuer.jwks)
    keys.load()
    verifier = TokenVerifier(keys, issuer=issuer.issuer, audience=issuer.audience)
    app = FastAPI()
    registry = HealthRegistry([HealthCheck("database", lambda: True, critical=True)])
    install_guard(app, verifier, "svc", registry, keys, open_paths=("/public",))

    @app.get("/thing")
    def thing(person=Depends(current_person)):
        return {"who": person.person_name, "admin": person.is_admin}

    @app.get("/public")
    def public():
        return {"open": True}

    @app.get("/public/more")
    def public_more():
        return {"open": True}

    @app.get("/admin")
    def admin(person=Depends(require_admin)):
        return {"ok": person.person_name}

    @app.get("/service")
    def service(person=Depends(service_only)):
        return {"ok": True}

    @app.get("/boom")
    def boom():
        raise RuntimeError("db password pw-123 leaked in a message")

    @app.get("/rid")
    def rid(request: Request):
        return {"rid": request.state.request_id}

    return TestClient(app, raise_server_exceptions=False)


service_only = require_client("modelhub-artifactory-service")


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_health_paths_need_no_token(client):
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200


def test_every_other_path_is_denied_without_a_token(client):
    r = client.get("/thing")
    assert r.status_code == 401
    assert r.json() == {"code": "token_invalid", "message": "Sign-in is required."}


def test_a_valid_token_reaches_the_handler_with_the_person(client, issuer):
    r = client.get("/thing", headers=auth(issuer.token(username="ada")))
    assert r.json() == {"who": "ada", "admin": False}


def test_a_bad_token_gets_the_same_minimal_answer_and_the_reason_goes_to_the_log(
    client, issuer, logbuf
):
    token = issuer.token(expires_in=-600)
    r = client.get("/thing", headers=auth(token))
    assert r.status_code == 401 and r.json()["code"] == "token_invalid"
    assert "expired" not in r.text
    log = logbuf.getvalue()
    assert '"event": "token_rejected"' in log and "expired" in log
    assert token not in log


def test_only_the_named_paths_are_open_not_their_children(client, issuer):
    assert client.get("/public").status_code == 200
    assert client.get("/public/more").status_code == 401


def test_a_non_bearer_scheme_is_refused(client, issuer):
    r = client.get("/thing", headers={"Authorization": "Basic abc"})
    assert r.status_code == 401


def test_admin_routes_refuse_a_person_without_the_role(client, issuer, logbuf):
    r = client.get("/admin", headers=auth(issuer.token(username="bob")))
    assert r.status_code == 403 and r.json()["code"] == "forbidden"
    assert '"event": "forbidden"' in logbuf.getvalue()


def test_admin_routes_accept_an_administrator(client, issuer):
    assert client.get("/admin", headers=auth(issuer.token(admin=True))).status_code == 200


def test_service_routes_refuse_a_person_and_accept_the_service_client(client, issuer):
    assert client.get("/service", headers=auth(issuer.token())).status_code == 403
    assert client.get("/service", headers=auth(issuer.service_token())).status_code == 200


def test_a_valid_request_id_is_kept_and_returned(client, issuer):
    r = client.get("/rid", headers={**auth(issuer.token()), "X-Request-Id": "req-42"})
    assert r.json()["rid"] == "req-42" and r.headers["X-Request-Id"] == "req-42"


def test_a_bad_request_id_is_replaced(client, issuer):
    r = client.get("/rid", headers={**auth(issuer.token()), "X-Request-Id": "bad id!"})
    assert r.headers["X-Request-Id"] != "bad id!" and len(r.headers["X-Request-Id"]) >= 8


def test_one_access_line_per_request_with_person_status_and_duration(client, issuer, logbuf):
    client.get("/thing", headers={**auth(issuer.token(username="ada")), "X-Request-Id": "r7"})
    lines = [json.loads(x) for x in logbuf.getvalue().splitlines()]
    access = [x for x in lines if x["event"] == "access"]
    assert len(access) == 1
    a = access[0]
    assert a["person"] == "ada" and a["status"] == 200 and a["path"] == "/thing"
    assert a["requestId"] == "r7" and a["duration_ms"] >= 0 and a["method"] == "GET"


def test_an_unhandled_error_is_a_plain_500_that_hides_the_detail(client, issuer, logbuf):
    r = client.get("/boom", headers=auth(issuer.token()))
    assert r.status_code == 500
    assert "pw-123" not in r.text
    assert r.json()["code"] == "internal_error"


def test_ready_is_503_when_the_key_set_is_empty(issuer, logbuf):
    def down():
        raise OSError

    keys = KeySet(down)
    keys.load()
    verifier = TokenVerifier(keys, issuer=issuer.issuer, audience=issuer.audience)
    app = FastAPI()
    install_guard(app, verifier, "svc", HealthRegistry([]), keys)
    c = TestClient(app)
    assert c.get("/healthz").status_code == 200
    assert c.get("/readyz").status_code == 503
