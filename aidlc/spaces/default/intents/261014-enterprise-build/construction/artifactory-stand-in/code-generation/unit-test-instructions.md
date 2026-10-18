# Unit Test Instructions: artifactory-stand-in

## Run this unit's tests

```bash
.venv/bin/python -m pytest server/stand_in -q --timeout=240
```

The command is scoped to this unit only. It needs `pip install -e server/testkit -e "server/stand_in[test]"` (the `test` extra brings `huggingface_hub` and `httpx`).

## Test framework and configuration

- pytest, tests in `server/stand_in/tests/`, written before the code (TDD, team practice).
- The stand-in starts itself on a free local port inside the tests (`StandIn` context manager); nothing outside the machine is reached.
- Integration tests drive the real `huggingface_hub` client (`upload_folder`, `snapshot_download`) against it, with Xet transfers disabled.

## Coverage targets

Standard strategy: five to eight tests per component plus integration tests for the key boundaries; the existing 86 tests stay green. No percentage floor is set by the team.

## Mocking and stubbing

No mocks: the unit is itself the stand-in. Failures are provoked with its own switches (`add_switch`, `set_write_allowed`, `set_overwrite_allowed`), not with patches.

## Test data

Small generated files written with `write_bytes` (so checksums are the same on Windows), and a fixed fake token per test; no real credentials.

## Platforms

Linux (the server job), Windows and macOS (the `stand-in` CI job).
