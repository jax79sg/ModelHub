"""The error-rate measure and the alert rules (catalog NFR6.3, NFR6.4; import service NFR6.4).

`deploy/monitoring/error_rate.py` takes the share of 5xx access lines from the services' JSON
logs; `deploy/monitoring/alerts.json` lists the alerts of the design with the signal each is read
from. Both are checked against access lines really made by the shared guard.
"""

import importlib.util
import io
import json
import logging
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from modelhub_common.guard import install_guard
from modelhub_common.health import HealthCheck, HealthRegistry
from modelhub_common.keys import KeySet
from modelhub_common.logs import JsonFormatter
from modelhub_common.tokens import TokenVerifier

MONITORING = Path(__file__).resolve().parents[3] / "deploy" / "monitoring"


def load_error_rate():
    spec = importlib.util.spec_from_file_location("error_rate", MONITORING / "error_rate.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["error_rate"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def real_lines(issuer):
    """Access lines written by the shared guard for 3 good requests and 1 server error."""
    stream = io.StringIO()
    logger = logging.getLogger("modelhub")
    old = (list(logger.handlers), logger.level, logger.propagate)
    logger.handlers.clear()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter("catalog"))
    logger.addHandler(handler)
    logger.setLevel("INFO")
    logger.propagate = False
    try:
        keys = KeySet(issuer.jwks)
        keys.load()
        verifier = TokenVerifier(keys, issuer=issuer.issuer, audience=issuer.audience)
        app = FastAPI()
        install_guard(
            app,
            verifier,
            "catalog",
            HealthRegistry([HealthCheck("database", lambda: True, critical=True)]),
            keys,
        )

        @app.get("/boom")
        def boom():
            raise RuntimeError("imitated")

        client = TestClient(app, raise_server_exceptions=False)
        for _ in range(3):
            assert client.get("/healthz").status_code == 200
        assert (
            client.get("/boom", headers={"Authorization": f"Bearer {issuer.token()}"}).status_code
            == 500
        )
        yield stream.getvalue()
    finally:
        logger.handlers[:] = old[0]
        logger.setLevel(old[1])
        logger.propagate = old[2]


def test_the_error_rate_is_the_share_of_5xx_access_lines_per_service(real_lines):
    rate = load_error_rate()
    prefixed = "\n".join(f"catalog-1  | {line}" for line in real_lines.splitlines())  # compose logs
    result = rate.error_rates(prefixed.splitlines())
    assert result["catalog"]["requests"] == 4
    assert result["catalog"]["errors"] == 1
    assert result["catalog"]["share"] == pytest.approx(0.25)


def test_lines_that_are_not_access_lines_or_not_json_are_ignored():
    rate = load_error_rate()
    lines = [
        "not json at all",
        json.dumps({"service": "portal", "event": "import_done", "status": 500}),
        json.dumps({"service": "portal", "event": "access", "status": 200}),
        json.dumps({"service": "portal", "event": "access", "status": 503}),
    ]
    result = rate.error_rates(lines)
    assert result["portal"]["requests"] == 2 and result["portal"]["errors"] == 1


def test_a_service_with_no_requests_is_not_reported_as_failing():
    rate = load_error_rate()
    assert rate.error_rates([]) == {}


def test_the_command_exits_1_above_a_threshold_and_0_below(tmp_path, real_lines):
    import subprocess

    log = tmp_path / "logs.txt"
    log.write_text(real_lines, encoding="utf-8")
    script = str(MONITORING / "error_rate.py")
    above = subprocess.run(
        [sys.executable, script, str(log), "--fail-above", "0.05"],
        capture_output=True,
        text=True,
        check=False,
    )
    below = subprocess.run(
        [sys.executable, script, str(log), "--fail-above", "0.50"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert above.returncode == 1 and "catalog" in above.stdout
    assert below.returncode == 0


EXPECTED = {
    "ready-down": ("health", "5 minutes"),
    "error-share": ("log", "10 minutes"),
    "list-slow": ("log", "10 minutes"),
    "import-interrupted": ("log", None),
    "disk-free": ("host", None),
    "artifactory-down": ("health", "10 minutes"),
}


def test_the_alert_rules_list_each_alert_of_the_design_with_its_signal():
    rules = json.loads((MONITORING / "alerts.json").read_text(encoding="utf-8"))["alerts"]
    by_id = {rule["id"]: rule for rule in rules}
    assert set(by_id) == set(EXPECTED)
    for name, (kind, window) in EXPECTED.items():
        assert by_id[name]["signal"]["kind"] == kind
        assert by_id[name].get("window") == window
        assert by_id[name]["targets"]  # which NFR it answers
    assert by_id["error-share"]["threshold"] == "5%" and by_id["list-slow"]["threshold"] == "800 ms"
    assert by_id["disk-free"]["threshold"] == "25%"


def test_the_signals_the_rules_read_really_exist(real_lines):
    first = json.loads(real_lines.splitlines()[0])
    assert {"event", "status", "duration_ms", "service"} <= set(first)  # error-share, list-slow
    importer = (MONITORING.parents[1] / "server" / "artifactory_service" / "src").rglob(
        "importer.py"
    )
    text = next(iter(importer)).read_text(encoding="utf-8")
    assert '"interrupted"' in text and '"artifactory_inconsistent"' in text  # import-interrupted
    service_main = (MONITORING.parents[1] / "server" / "artifactory_service" / "src").rglob(
        "main.py"
    )
    assert 'HealthCheck("artifactory"' in next(iter(service_main)).read_text(encoding="utf-8")
