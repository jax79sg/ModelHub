"""login, logout and import (rules BR1.1 to BR1.14 of the import-cli unit)."""

import json
import os
import stat
import sys

import httpx
import pytest
from fake_import_service import FakeImportService
from typer.testing import CliRunner

from modelhub import cli, importer, settings, signing

runner = CliRunner()
SECRET = "mhi_" + "q7Zk" * 8


@pytest.fixture
def service(monkeypatch):
    fake = FakeImportService()

    def make(client_settings):
        return importer.ServiceClient(
            client_settings.server,
            client_settings.token,
            http=httpx.Client(transport=fake.transport()),
            sleep=fake.sleeps.append,
            jitter=lambda: 0,
        )

    fake.sleeps = []
    monkeypatch.setattr(cli, "make_service_client", make)
    monkeypatch.setattr(importer.time, "sleep", fake.sleeps.append)
    return fake


@pytest.fixture
def config(tmp_path, monkeypatch):
    folder = tmp_path / "config"
    monkeypatch.setenv("MODELHUB_CONFIG_DIR", str(folder))
    for name in ("MODELHUB_SERVER", "MODELHUB_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    return folder


@pytest.fixture
def run(home, key_id, config):
    def _run(*args, input=None, env=None):
        return runner.invoke(
            cli.app,
            [str(a) for a in args],
            input=input,
            env={"MODELHUB_HOME": str(home), "MODELHUB_CONFIG_DIR": str(config), **(env or {})},
        )

    _run.key_id = key_id
    return _run


@pytest.fixture
def bundled(run, pulled, tmp_path):
    out = tmp_path / "out"
    result = run("bundle", pulled, "--out", out, "--piece-size", "4KiB", "--key", run.key_id)
    assert result.exit_code == 0, result.output
    doc = signing.find_own_key(run.key_id)
    signing.trust_key(doc, doc["fingerprint"])  # this computer trusts its own key
    return out


@pytest.fixture
def signed_in(config):
    settings.save("https://modelhub.example.org", SECRET)


def descriptions(folder):
    return sorted(folder.glob("*.bundle.json"))


# --- login and logout (BR1.1, BR1.2) -----------------------------------------------------------
def test_login_saves_privately_and_never_prints_the_token(run, config):
    result = run("login", input=f"https://modelhub.example.org\n{SECRET}\n")
    assert result.exit_code == 0, result.output
    assert SECRET not in result.output
    path = config / "settings.json"
    assert json.loads(path.read_text())["token"] == SECRET
    if sys.platform != "win32":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_login_trims_a_pasted_token_and_refuses_plain_http_except_for_localhost(run, config):
    assert run("login", input=f"https://m.example.org\n  {SECRET} \n").exit_code == 0
    assert json.loads((config / "settings.json").read_text())["token"] == SECRET
    refused = run("login", input=f"http://m.example.org\n{SECRET}\n")
    assert refused.exit_code == 2 and "https" in refused.output
    assert run("login", input=f"http://localhost:8000\n{SECRET}\n").exit_code == 0
    assert run("login", input=f"http://127.0.0.1:8000\n{SECRET}\n").exit_code == 0


@pytest.mark.skipif(sys.platform == "win32", reason="permission bits")
def test_if_the_permission_cannot_be_set_nothing_is_saved(run, config, monkeypatch):
    real = os.chmod

    def broken(path, mode, **kw):
        if str(path).endswith("settings.json"):
            return real(path, 0o644, **kw)
        return real(path, mode, **kw)

    monkeypatch.setattr(settings.Path, "chmod", lambda self, mode: broken(self, mode))
    result = run("login", input=f"https://m.example.org\n{SECRET}\n")
    assert result.exit_code == 2 and not (config / "settings.json").exists()


def test_a_token_cannot_be_given_on_the_command_line(run, bundled):
    for args in (("login", "--token", SECRET), ("import", str(bundled), "--token", SECRET)):
        result = run(*args)
        assert result.exit_code == 2 and "modelhub login" in result.output
        assert SECRET not in result.output


def test_logout_deletes_the_settings(run, config, signed_in):
    assert (config / "settings.json").exists()
    assert run("logout").exit_code == 0 and not (config / "settings.json").exists()
    assert "No saved settings" in run("logout").output


def test_environment_variables_override_the_file(run, service, bundled, signed_in):
    service.skip = True
    result = run(
        "import",
        bundled,
        env={"MODELHUB_SERVER": "https://other.example.org", "MODELHUB_TOKEN": "mhi_other"},
    )
    assert result.exit_code == 0, result.output
    assert service.headers[0]["authorization"] == "Bearer mhi_other"


# --- starting (BR1.3, BR1.13) ------------------------------------------------------------------
def test_without_settings_it_says_run_login_before_reading_anything(run, bundled):
    result = run("import", bundled)
    assert result.exit_code == 2 and "modelhub login" in result.output


def test_no_bundle_is_exit_2(run, signed_in, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert run("import", empty).exit_code == 2
    assert run("import").exit_code == 2


def test_from_store_is_reserved(run, signed_in, tmp_path):
    result = run("import", "--from-store", tmp_path)
    assert result.exit_code == 2 and "not available" in result.output


def test_a_refused_token_stops_the_whole_run_with_the_service_message(
    run, service, bundled, signed_in
):
    service.create_error = (
        401,
        {
            "code": "token_invalid",
            "message": "This token is not accepted. Make a new token in the portal.",
            "retryable": False,
        },
    )
    result = run("import", bundled)
    assert result.exit_code == 2 and "Make a new token" in result.output


def test_a_program_that_is_too_old_stops_the_run(run, service, bundled, signed_in):
    service.create_error = (
        426,
        {"code": "client_too_old", "message": "Update to 9.9.9.", "retryable": False},
    )
    result = run("import", bundled)
    assert result.exit_code == 2 and "9.9.9" in result.output
    assert service.headers[0]["x-modelhub-client"]


# --- the happy path and the report (BR1.4, BR1.5, BR1.9) ----------------------------------------
def test_a_bundle_is_checked_sent_started_and_reported(run, service, bundled, signed_in):
    result = run("import", bundled)
    assert result.exit_code == 0, result.output
    assert (
        "IMPORTED" in result.output
        and "1 imported, 0 completed, 0 skipped, 0 failed" in result.output
    )
    assert SECRET not in result.output
    body = service.bodies[0]
    assert body["modelId"] and len(body["commit"]) == 40 and body["checkResults"]["pieces"] >= 1
    puts = [c for c in service.calls if c[0] == "PUT"]
    assert [int(p[1].rsplit("/", 1)[1]) for p in puts] == list(range(1, len(puts) + 1))
    assert service.started


def test_a_bundle_named_by_its_first_piece_or_its_description_is_found(
    run, service, bundled, signed_in
):
    piece = min(bundled.glob("*.part-*"))
    assert run("import", piece).exit_code == 0
    assert run("import", descriptions(bundled)[0]).exit_code == 0


def test_an_already_imported_model_is_skipped_and_nothing_is_sent(run, service, bundled, signed_in):
    service.skip = True
    result = run("import", bundled)
    assert (
        result.exit_code == 0 and "SKIPPED" in result.output and "already imported" in result.output
    )
    assert not [c for c in service.calls if c[0] == "PUT"]


def test_only_the_missing_pieces_are_sent_on_a_rerun(run, service, bundled, signed_in):
    first = run("import", bundled)
    assert first.exit_code == 0
    sent = len([c for c in service.calls if c[0] == "PUT"])
    assert sent >= 2
    service.calls.clear()
    assert run("import", bundled).exit_code == 0
    assert not [c for c in service.calls if c[0] == "PUT"]  # all stored: none sent again


def test_completed_says_which_kind(run, service, bundled, signed_in):
    service.final = {"state": "done", "outcome": "completed", "plan": "finish"}
    assert "already in Artifactory; record completed" in run("import", bundled).output
    service.final = {"state": "done", "outcome": "completed", "plan": "repair"}
    assert "files uploaded again; record kept" in run("import", bundled).output


def test_a_service_failure_is_a_failed_entry_with_its_reason_and_exit_1(
    run, service, bundled, signed_in
):
    service.final = {
        "state": "failed",
        "outcome": "failed",
        "error": {
            "code": "artifactory_conflict",
            "message": "Artifactory refused the upload.",
            "retryable": False,
        },
    }
    result = run("import", bundled)
    assert (
        result.exit_code == 1
        and "FAILED" in result.output
        and "Artifactory refused" in result.output
    )


def test_progress_is_polled_until_the_service_ends_it(run, service, bundled, signed_in):
    service.polls_before_done = 3
    assert run("import", bundled).exit_code == 0
    assert len([c for c in service.calls if c[0] == "GET"]) == 3
    assert 2 in service.sleeps


# --- one failure does not stop the rest (BR1.4, BR1.11) ------------------------------------------
def test_a_damaged_bundle_fails_alone_and_the_others_go_on(
    run, service, bundled, tmp_path, signed_in
):
    broken = tmp_path / "broken"
    broken.mkdir()
    for f in bundled.iterdir():
        (broken / f.name).write_bytes(f.read_bytes())
    next(broken.glob("*.part-*")).write_bytes(b"damaged")
    result = run("import", broken, bundled)
    assert result.exit_code == 1, result.output
    assert "FAILED" in result.output and "IMPORTED" in result.output
    assert result.output.index("FAILED") < result.output.index("IMPORTED")  # in the order given
    assert service.calls[0][0] == "POST"  # the first thing sent was for the good one


def test_an_untrusted_signature_is_refused_before_anything_is_sent(
    run, service, bundled, signed_in, home
):
    run("key", "untrust", run.key_id)
    result = run("import", bundled)
    assert result.exit_code == 1 and not service.calls


# --- retries and waiting (BR1.6, BR1.7) ---------------------------------------------------------
def test_network_trouble_is_retried_with_growing_waits(run, service, bundled, signed_in):
    service.flaky = 3
    assert run("import", bundled).exit_code == 0
    assert service.sleeps[:3] == [1, 2, 4]


def test_after_five_retries_the_model_fails_and_the_run_goes_on(run, service, bundled, signed_in):
    service.flaky = 99
    result = run("import", bundled)
    assert result.exit_code == 1 and "could not be reached" in result.output
    assert service.sleeps == [1, 2, 4, 8, 16]


def test_a_non_retryable_answer_fails_at_once_with_the_service_words(
    run, service, bundled, signed_in
):
    service.create_error = (
        409,
        {
            "code": "model_locked",
            "message": "Another import of org/tiny is running.",
            "retryable": False,
        },
    )
    result = run("import", bundled)
    assert result.exit_code == 1 and "Another import" in result.output and not service.sleeps


def test_a_wrong_piece_is_sent_once_more_then_the_model_fails(run, service, bundled, signed_in):
    bad = {"code": "piece_mismatch", "message": "bad piece", "retryable": False}
    service.piece_failures = [(409, bad)]
    assert run("import", bundled).exit_code == 0
    service.stored.clear()
    service.piece_failures = [(409, bad), (409, bad)]
    result = run("import", bundled)
    assert result.exit_code == 1 and "bad piece" in result.output


def test_a_busy_service_is_waited_for_every_60_seconds(run, service, bundled, signed_in):
    service.busy_starts = 2
    assert run("import", bundled).exit_code == 0
    assert service.sleeps.count(60) == 2


def test_a_service_that_stays_busy_fails_the_model_after_30_minutes(
    run, service, bundled, signed_in, monkeypatch
):
    service.busy_starts = 10_000
    now = [0.0]
    monkeypatch.setattr(importer.time, "monotonic", lambda: now[0])
    service.sleeps = []
    monkeypatch.setattr(
        importer.time, "sleep", lambda s: (service.sleeps.append(s), now.__setitem__(0, now[0] + s))
    )
    result = run("import", bundled)
    assert result.exit_code == 1 and "stayed busy" in result.output
    assert 29 <= service.sleeps.count(60) <= 31


def test_a_certificate_problem_is_not_retried(run, service, bundled, signed_in, monkeypatch):
    import ssl

    def refuse(request):
        raise httpx.ConnectError("tls") from ssl.SSLError("certificate verify failed")

    service.transport = lambda: httpx.MockTransport(refuse)
    result = run("import", bundled)
    assert result.exit_code == 1 and "certificate" in result.output and not service.sleeps


# --- interrupt (BR1.8) -------------------------------------------------------------------------
def test_ctrl_c_leaves_the_import_and_says_how_to_resume(
    run, service, bundled, signed_in, monkeypatch
):
    original = service._handle

    def stop_on_start(request):
        if request.url.path.endswith("/start"):
            raise KeyboardInterrupt
        return original(request)

    service._handle = stop_on_start
    result = run("import", bundled)
    assert result.exit_code == 130
    assert "again" in result.output and "Not finished" in result.output
    assert not [c for c in service.calls if c[0] == "DELETE"]


# --- secrecy (BR1.2) ---------------------------------------------------------------------------
def test_the_token_never_appears_even_in_server_messages(run, service, bundled, signed_in):
    service.create_error = (
        400,
        {"code": "bad", "message": f"Bearer {SECRET} was weird {SECRET}", "retryable": False},
    )
    result = run("import", bundled)
    assert SECRET not in result.output
