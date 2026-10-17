# Unit Test Instructions: import-cli

## Run this unit's tests

```bash
.venv/bin/python -m pytest tests/test_import_cli.py -q --timeout=300
```

Scoped to this unit's test file. Install first: `pip install -e ".[dev]"`. The command needs no network, Docker or database. The rest of the CLI suite (`tests/`) must stay green and is run by the Build and Test stage.

## Test framework and configuration

- pytest, `tests/test_import_cli.py`, written before the code (TDD, team practice), using the existing `home`, `key_id` and `pulled` fixtures to make and sign real bundles.
- A fake import service (`tests/fake_import_service.py`) answers the C1 calls through an `httpx` mock transport and has switches for skipped, locked, busy, flaky and damaged cases. An end-to-end test of this client against the real service lives in the artifactory-service unit.

## Coverage targets

Standard strategy: five to eight tests per component plus integration at the service boundary; 29 tests, one per rule of the unit's design (BR1.1 to BR1.14), with retries and waits driven by an injected sleep so no test really waits.

## Mocking and stubbing

Only the service boundary is faked (the fake service); signing, bundling and verification are the real code. Time and sleep are injected.

## Test data

Bundles are made at run time with the program's own `bundle` command; tokens are generated, not fixed strings.
