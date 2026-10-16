"""Retention: the period, the due list, keep and remove decisions (BR1.10, BR1.15-BR1.18)."""

from datetime import timedelta

import pytest
from modelhub_artifactory_service.catalog_client import CatalogClient
from modelhub_artifactory_service.gateway import ArtifactoryUnreachable, Gateway
from modelhub_artifactory_service.retention import Retention, RetentionError
from modelhub_stand_in.server import StandIn
from test_catalog_client import DOCS, record

MODEL = "acme/tiny"
C1 = "1" * 40
FILES = {"config.json": b'{"a": 1}', "model.bin": b"M" * 100}


@pytest.fixture
def stand_in(tmp_path):
    with StandIn(token="svc-token-1", workdir=tmp_path / "si") as s:
        yield s


@pytest.fixture(autouse=True)
def _no_xet(monkeypatch):
    monkeypatch.setenv("HF_HUB_DISABLE_XET", "1")


@pytest.fixture
def world(pool, clock, catalog, issuer, stand_in, tmp_path):
    gateway = Gateway(stand_in.url, stand_in.repo_key, stand_in.token)
    client = CatalogClient(catalog, "", lambda: issuer.service_token())
    folder = tmp_path / "up"
    folder.mkdir()
    for name, data in FILES.items():
        (folder / name).write_bytes(data)
    gateway.uploader.upload(folder, MODEL, C1)
    return Retention(pool, gateway, client, clock)


def imported_at(clock, days_ago):
    return (clock() - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def put(world, clock, days_ago):
    rec = record(importedAt=imported_at(clock, days_ago))
    world.catalog.put_version(MODEL, C1, rec, DOCS)


def test_the_period_starts_at_365_and_changes_within_1_to_3650(world):
    assert world.settings()["periodDays"] == 365
    out = world.set_period(30, "root")
    assert out["periodDays"] == 30 and out["changedBy"] == "root"
    for bad in (0, 3651, "x", None):
        with pytest.raises(RetentionError) as err:
            world.set_period(bad, "root")
        assert err.value.status == 422


def test_only_versions_older_than_the_period_are_due(world, clock):
    put(world, clock, days_ago=400)
    due = world.due()
    assert [d["modelId"] for d in due] == [MODEL] and due[0]["ageDays"] >= 399
    world.set_period(500, "root")
    assert world.due() == []


def test_keep_takes_the_version_off_the_list_until_the_period_passes_again(world, clock):
    put(world, clock, days_ago=400)
    out = world.decide(MODEL, C1, "keep", "u9", "root")
    assert out["outcome"] == "kept"
    assert world.due() == []
    clock.advance(days=366)
    assert [d["commit"] for d in world.due()] == [C1]


def test_remove_deletes_the_files_then_marks_the_catalog(world, clock, stand_in):
    put(world, clock, days_ago=400)
    out = world.decide(MODEL, C1, "remove", "u9", "root")
    assert out["outcome"] == "removed"
    assert world.gateway.list_version(MODEL, C1).state == "absent"
    assert world.catalog.get_version(MODEL, C1)["state"] == "removed"
    assert world.decisions()[0]["outcome"] == "done"


def test_a_failed_deletion_leaves_it_listed_and_the_catalog_untouched(world, clock):
    put(world, clock, days_ago=400)

    def boom(listing):
        raise ArtifactoryUnreachable("down")

    world.gateway.delete_version = boom
    out = world.decide(MODEL, C1, "remove", "u9", "root")
    assert out["outcome"] == "removal_failed"
    assert world.catalog.get_version(MODEL, C1)["state"] == "imported"
    assert world.decisions()[0]["outcome"] == "failed" and len(world.due()) == 1


def test_files_deleted_but_not_marked_is_repeated_at_the_catalog_step_only(world, clock):
    put(world, clock, days_ago=400)
    real = world.catalog.mark_removed
    world.catalog.mark_removed = lambda *a: "conflict"
    out = world.decide(MODEL, C1, "remove", "u9", "root")
    assert out["outcome"] == "removal_failed"
    assert world.decisions()[0]["outcome"] == "files_deleted_not_marked"
    world.catalog.mark_removed = real
    calls = []
    world.gateway.delete_version = lambda listing: calls.append(listing) or "deleted"
    assert world.decide(MODEL, C1, "remove", "u9", "root")["outcome"] == "removed"
    assert calls == []  # the files were already gone: only the Catalog step was repeated


def test_a_decision_for_a_version_that_is_not_imported_is_409(world, clock):
    with pytest.raises(RetentionError) as err:
        world.decide(MODEL, "2" * 40, "keep", "u9", "root")
    assert err.value.status == 409
    put(world, clock, days_ago=400)
    world.decide(MODEL, C1, "remove", "u9", "root")
    with pytest.raises(RetentionError) as err:
        world.decide(MODEL, C1, "keep", "u9", "root")
    assert err.value.status == 409


def test_a_bad_decision_word_is_422_and_decisions_list_newest_first(world, clock):
    put(world, clock, days_ago=400)
    with pytest.raises(RetentionError) as err:
        world.decide(MODEL, C1, "maybe", "u9", "root")
    assert err.value.status == 422
    world.decide(MODEL, C1, "keep", "u9", "root")
    clock.advance(minutes=1)
    world.decide(MODEL, C1, "keep", "u9", "ada")
    got = world.decisions()
    assert [d["decidedBy"] for d in got] == ["ada", "root"]
    assert world.decisions(model=MODEL, person="root")[0]["decidedBy"] == "root"
