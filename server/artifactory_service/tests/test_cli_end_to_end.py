"""The real import command against the real service, Catalog and Artifactory stand-in (C1).

This is the first end-to-end proof: a signed bundle made by the program goes in through the
program's own client and comes out as a Catalog record and files in Artifactory.
"""

import pytest
from fastapi.testclient import TestClient
from modelhub_artifactory_service.app import create_app
from modelhub_artifactory_service.retention import Retention

from modelhub import importer, signing


@pytest.fixture(autouse=True)
def import_computer(bundle, tmp_path, monkeypatch):
    """The import computer trusts the bundle's key, as after `modelhub key trust`."""
    monkeypatch.setenv("MODELHUB_HOME", str(tmp_path / "import-computer"))
    signing.trust_key(bundle.public_key, bundle.public_key["fingerprint"])


@pytest.fixture
def cli_client(world, catalog, issuer):
    app = create_app(
        world,
        Retention(world.pool, world.gateway, world.catalog, world.clock),
        world.keys,
        world.catalog,
        jwks_fetch=issuer.jwks,
        issuer=issuer.issuer,
        audience=issuer.audience,
        runner=lambda fn: fn(),
    )
    token = catalog.post(
        "/v1/tokens",
        json={"name": "cli"},
        headers={"Authorization": f"Bearer {issuer.token(username='ada', sub='u1')}"},
    ).json()["token"]
    http = TestClient(app)
    return importer.ServiceClient("http://testserver", token, http=http, sleep=lambda s: None)


def test_a_bundle_goes_in_and_a_second_run_is_skipped(cli_client, bundle, world):
    first = importer.run(
        cli_client, [bundle.description_path], sleep=lambda s: None, clock=lambda: 0.0
    )
    assert [e.result for e in first.entries] == ["imported"], first.entries
    assert world.gateway.list_version(bundle.model_id, bundle.commit).state == "present"
    assert world.catalog.get_version(bundle.model_id, bundle.commit)["state"] == "imported"
    again = importer.run(
        cli_client, [bundle.description_path], sleep=lambda s: None, clock=lambda: 0.0
    )
    assert [e.result for e in again.entries] == ["skipped"]


def test_a_refused_token_stops_the_run(cli_client, bundle):
    bad = importer.ServiceClient("http://testserver", "mhi_unknown", http=cli_client._http)
    with pytest.raises(importer.RunStopped):
        importer.run(bad, [bundle.description_path], sleep=lambda s: None)
