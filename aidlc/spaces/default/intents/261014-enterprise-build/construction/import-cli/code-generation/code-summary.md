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

33 tests in `tests/test_import_cli.py` (29 re-run for the replay plus 4 added by loop-back 1) against a fake import service, plus the end-to-end test of this client against the real service in the artifactory-service unit. Re-run for this replay.

## Loop-back 1 (from Build and Test)

Build and Test found NFR6.3 Not Met: the import command wrote no run record. It now writes the existing `run-record.json` in the folder the command is run from, one line per model (model, commit, result, reason, service code), also when a run is interrupted; the record is redacted like every other output, so the token never appears. Nothing is written when the run cannot start. Tests: four in `tests/test_import_cli.py`.

## Loop-back 2

Build and Test left eight import command targets Unverified; seven are now checked by eight tests in `tests/test_import_limits.py` (CLI suite: 474 passed). A real gap was found and fixed: the command asked the service for the result every 2 seconds, so with a slow link the report could come more than 2 seconds after the service said done (tested up to 2.3 s); it now asks every second (`POLL_SECONDS = 1`), worst case 1.3 s with a 0.3 s request (NFR1.1). The real command was killed with its process killed during create, during a piece and during the wait, then run again against the same service: it ended imported and sent only the pieces the service was missing (NFR4.2). A declared set of 200 pieces of 1 GB (200 GB) with three sent keeps the client below 150 MB at peak, with 1 MiB blocks (NFR7.1). Memory per piece in the client is under 1 KiB, so 999,999 pieces stays under 1 GB, but it is not literally constant: a bundle's piece list is held in memory (NFR7.3, flagged). Fifty bundles in a row grow memory by under 2 MB (NFR7.4). With a real HTTP connection and every other socket refused, the command contacts only the configured server (NFR5.6, NFR8.1). Still Unverified and named: NFR7.2 link speed on a real 1 Gbit/s link. The existing test that expected a 2 second poll now expects `POLL_SECONDS`. No target was weakened.

## Deviations from the plan

None for the unit. This record was written afterwards, in a replay through the engine; the unit was built earlier without it (see the stage diary).
