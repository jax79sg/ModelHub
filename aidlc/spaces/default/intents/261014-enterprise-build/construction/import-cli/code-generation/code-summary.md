# Code Summary: import-cli

## What was built

The import command, built and merged before this replay (PR #15).

- `settings.py` - the server address and personal token saved only by `login`, in the person's own settings folder, owner-only (nothing saved if the permission cannot be set); environment overrides.
- `importer.py` - find bundles, verify each here, create the import, send only the missing pieces one at a time with their checksum, start, watch, report; retries, busy waiting, 401 and 426 stopping the run, Ctrl-C leaving the import to resume.
- `cli.py` - `login`, `logout`, `import` (`--from-store` reserved, a token option refused).
- `verify.py` - `only=` so one bundle in a crowded folder is not re-hashed with the others.

## Key decisions

- `httpx` is a direct dependency (it already came with `huggingface_hub`).
- Waits and the clock are injected, so no test really waits; the token is redacted from everything printed.
- A mismatched piece is sent once more, then the model fails; an empty list of missing pieces means nothing is sent (a bug found by a test).

## Test coverage summary

29 tests in `tests/test_import_cli.py` against a fake import service, plus the end-to-end test of this client against the real service in the artifactory-service unit. Re-run for this replay.

## Deviations from the plan

None for the unit. This record was written afterwards, in a replay through the engine; the unit was built earlier without it (see the stage diary).
