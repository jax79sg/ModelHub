"""Failure switches (BR1.10), the register and checklist (BR1.13), start and stop (BR1.14)."""

import re
import time
from pathlib import Path

import httpx
import pytest
from modelhub_stand_in import app as app_module
from modelhub_stand_in.register import checklist, checklist_markdown, load
from modelhub_stand_in.server import StandIn
from modelhub_stand_in.switches import KINDS, SwitchTable


def get(s, path="/api/models/acme/x", **kw):
    return httpx.get(s.hf_endpoint + path, headers={"Authorization": f"Bearer {s.token}"}, **kw)


# --- switches ---------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "kind,status",
    [
        ("unauthorised", 401),
        ("forbidden", 403),
        ("conflict", 409),
        ("name-refused", 400),
        ("server-error", 500),
    ],
)
def test_each_status_switch_answers_its_status_once_and_records_it(stand_in, kind, status):
    stand_in.add_switch(kind)
    assert get(stand_in).status_code == status
    assert get(stand_in).status_code == 404  # cleared after one use: a normal answer
    assert stand_in.calls[0]["switch_fired"] == kind


def test_the_switch_fires_after_n_matching_calls(stand_in):
    stand_in.add_switch("server-error", after_calls=2)
    assert [get(stand_in).status_code for _ in range(4)] == [404, 404, 500, 404]


def test_times_and_sticky(stand_in):
    stand_in.add_switch("server-error", times=2)
    assert [get(stand_in).status_code for _ in range(3)] == [500, 500, 404]
    stand_in.add_switch("server-error", sticky=True)
    assert [get(stand_in).status_code for _ in range(3)] == [500, 500, 500]
    stand_in.clear_switches()
    assert get(stand_in).status_code == 404


def test_a_scope_only_matches_its_own_calls(stand_in):
    stand_in.add_switch("server-error", scope="delete")
    assert get(stand_in).status_code == 404  # a listing call is not a delete
    assert stand_in.delete_version("acme/x", "a" * 40) == 500


def test_slow_holds_the_answer(stand_in):
    stand_in.add_switch("slow", seconds=0.4)
    start = time.monotonic()
    get(stand_in)
    assert time.monotonic() - start >= 0.35


def test_a_switch_is_checked_before_the_token(stand_in):
    stand_in.add_switch("server-error")
    r = httpx.get(stand_in.hf_endpoint + "/api/models/a/b", headers={"Authorization": "Bearer x"})
    assert r.status_code == 500


def test_unknown_kind_and_scope_are_refused():
    table = SwitchTable()
    with pytest.raises(ValueError):
        table.add("explode")
    with pytest.raises(ValueError):
        table.add("slow", scope="everywhere")


def test_every_kind_in_the_design_exists():
    assert set(KINDS) == {
        "unauthorised",
        "forbidden",
        "conflict",
        "name-refused",
        "server-error",
        "slow",
        "cut-transfer",
        "half-version",
    }


def test_control_address_sets_and_lists_calls_for_other_processes(stand_in):
    h = {"Authorization": f"Bearer {stand_in.token}"}
    r = httpx.post(f"{stand_in.url}/__control/switches", json={"kind": "server-error"}, headers=h)
    assert r.status_code == 200
    assert get(stand_in).status_code == 500
    calls = httpx.get(f"{stand_in.url}/__control/calls", headers=h).json()
    assert calls[0]["status"] == 500
    assert httpx.get(f"{stand_in.url}/__control/calls").status_code == 401


# --- register and checklist -------------------------------------------------------------------
def test_every_answer_the_stand_in_can_give_has_a_register_entry():
    source = Path(app_module.__file__).read_text()
    given = set(re.findall(r'error\(\s*(\d{3}),\s*"([a-z_]+)"', source))
    registered = {a for entry in load() for a in entry["answers"]}
    registered_pairs = {tuple(a.split(" ", 1)) for a in registered}
    missing = sorted(p for p in given if p not in registered_pairs)
    assert not missing, f"answers with no assumption entry: {missing}"


def test_register_entries_are_complete():
    seen = set()
    for entry in load():
        assert entry["id"] not in seen
        seen.add(entry["id"])
        assert entry["basis"] in ("documented", "inferred", "invented")
        assert entry["behaviour"] and "confirm_on_real" in entry
        if entry["confirm_on_real"]:
            assert entry["check"], f"{entry['id']} needs a 'what to check' line"


def test_the_checklist_lists_exactly_the_entries_to_confirm():
    ids = {c["assumption"] for c in checklist()}
    assert ids == {a["id"] for a in load() if a["confirm_on_real"]}
    assert all(c["confirmed"] == "open" for c in checklist())


def test_the_checklist_covers_the_undocumented_layout():
    assert any(c["assumption"] == "A9" for c in checklist())
    assert "A9" in checklist_markdown()


# --- start, stop, isolation -------------------------------------------------------------------
def test_it_refuses_to_listen_on_anything_but_the_local_machine():
    with pytest.raises(ValueError):
        StandIn(token="t", host="0.0.0.0")


def test_it_refuses_an_empty_token():
    with pytest.raises(ValueError):
        StandIn(token="")


def test_it_starts_empty_for_each_test_and_removes_its_folder_on_stop():
    with StandIn(token="t-9") as a:
        folder = a.workdir
        assert folder.exists() and a.repositories() == []
        assert a.calls == []
    assert not folder.exists()


def test_it_starts_quickly_and_binds_to_loopback_only():
    start = time.monotonic()
    with StandIn(token="t-10") as s:
        assert get(s).status_code == 404
        assert time.monotonic() - start < 2
        assert s.url.startswith("http://127.0.0.1:")


def test_it_does_not_read_the_environment_for_a_token(monkeypatch):
    monkeypatch.setenv("ARTIFACTORY_TOKEN", "from-the-environment")
    with StandIn(token="given-by-test") as s:
        r = httpx.get(
            s.hf_endpoint + "/api/models/a/b",
            headers={"Authorization": "Bearer from-the-environment"},
        )
        assert r.status_code == 401


def test_the_checklist_prints_from_the_command_line(capsys):
    from modelhub_stand_in.__main__ import main

    assert main(["--checklist"]) == 0
    assert "Checklist for a real Artifactory" in capsys.readouterr().out
