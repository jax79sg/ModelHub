# Build Instructions

## Dependencies

- Python 3.10 or newer and the project's virtual environment: `python -m venv .venv && .venv/bin/pip install -e ".[dev]" -e server/testkit -e server/common -e "server/stand_in[test]" -e web -e server/catalog -e server/artifactory_service -e server/portal`.
- For the real Keycloak tests: Docker with Compose, Google Chrome, and `pip install playwright` (the tests use the installed Chrome; nothing is downloaded by Playwright). PostgreSQL for the server tests comes from Docker or `MODELHUB_TEST_POSTGRES_URL`.

## Build

This unit builds no program. Its files are configuration (`deploy/keycloak/`) and tests. The checks that stand for a build: `ruff check .` and `ruff format --check .`, and `docker compose -f deploy/keycloak/compose.keycloak.yaml config --quiet`.

## Build verification

`.venv/bin/python -m pytest tests/test_keycloak_files.py -q` (files, no Docker needed for most) and the compose file reading cleanly.

## Troubleshooting

- Port 8080 busy: the real tests skip with a message; stop what uses it.
- Keycloak refuses the realm file: its logs (`docker compose -f deploy/keycloak/compose.keycloak.yaml logs`) name the offending field (it once named `description`).
- The name `keycloak` does not resolve in a browser: add `127.0.0.1 keycloak modelhub.test` to the hosts file.
