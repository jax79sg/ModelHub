# Build Instructions

## Prerequisites

- Python 3.10 or later (3.12 for the images), Docker for the PostgreSQL-backed tests and the image build, `bash` and `openssl` for the deployment scripts.
- No internet is needed after the dependencies are installed.

## Install and build

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pip install -e web -e server/testkit -e server/common -e server/catalog \
  -e server/stand_in -e server/artifactory_service -e server/portal
```

Lint and format check (the build's gate): `.venv/bin/ruff check . && .venv/bin/ruff format --check .`

Images (CI builds them on every change; building them locally needs Docker):

```bash
for unit in catalog artifactory_service portal; do
  docker build -f deploy/Dockerfile --build-arg UNIT=$unit -t modelhub/${unit//_/-}:dev .
done
docker build -f deploy/proxy/Dockerfile -t modelhub/proxy:dev .
```

## Build verification

`ruff` clean; `pip install` of each package succeeds; the CI `images` job builds the four images, checks that no stand-in or test helper is inside, that none runs as root, scans them, and starts the whole stack.

## Troubleshooting

- A test that needs PostgreSQL skips with a clear message when Docker is missing; set `MODELHUB_TEST_POSTGRES_URL` to use another server.
- `pytest server` as one run collides on shared test file names; run each unit on its own (as CI does).
- If Docker hangs, do not restart it from a script; stop and tell the person.
