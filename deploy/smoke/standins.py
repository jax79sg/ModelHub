"""Both outside systems for the smoke test: a sign-in stand-in and an Artifactory stand-in."""

import time
from pathlib import Path

from modelhub_stand_in.server import StandIn
from modelhub_testkit.keycloak import KeycloakServer

token = Path("/run/secrets/artifactory_token").read_text().strip()
keycloak = KeycloakServer(host="0.0.0.0", public_host="standins", port=9000).start()
artifactory = StandIn(
    token=token,
    repo_key="hf-local",
    host="0.0.0.0",
    public_host="standins",
    port=9100,
    allow_any_host=True,
).start()
print(
    f"sign-in stand-in at {keycloak.realm}; Artifactory stand-in at {artifactory.url}", flush=True
)
while True:
    time.sleep(3600)
