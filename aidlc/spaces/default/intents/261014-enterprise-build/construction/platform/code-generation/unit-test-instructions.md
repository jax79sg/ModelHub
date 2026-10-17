# Unit Test Instructions: platform

## Run this unit's tests

```bash
.venv/bin/python -m pytest tests/test_deploy_definition.py tests/test_build_pack.py tests/test_serverpack.py -q --timeout=300
```

Scoped to this unit's test files. Install first: `pip install -e ".[dev]"` (it brings `pyyaml`). No Docker or network is needed: the pack-building tests run `deploy/build-pack.sh` against a stubbed `docker`. Also part of this unit: `tests/test_loop_guard.py` (the workflow tooling) and the whole-stack check `server/e2e` (needs Docker for PostgreSQL).

## Test framework and configuration

- pytest, written before the code (TDD, team practice).
- The deployment files are checked as data (Compose, nginx and Dockerfile); the pack is made and verified with a real key made in a private home folder.
- What only a real Docker host can prove (the image build, scan, smoke test, upgrade-and-return rehearsal) runs in the CI `images` job (`deploy/smoke/run.sh`).

## Coverage targets

Standard strategy: five to eight tests per component plus integration at the Docker boundary (in CI); 52 tests here. The rehearsal retags the same images as the new release, so it proves the procedure and that data survives, not a schema change.

## Mocking and stubbing

Only `docker` is stubbed (a small script on `PATH`) so the pack script's flow and its output can be checked without a daemon.

## Test data

Pack contents are tiny generated files; keys are made in a temporary home folder; secrets are generated at run time.
