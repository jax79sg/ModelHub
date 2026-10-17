# Code Summary: artifactory-stand-in

## What was built

A test-only imitation of Artifactory's Hugging Face repository, built before this replay and merged in PR #11, with later additions in PRs #13 (a storage-listing route without a path, a `url` in the repository-exists answer) and #19 (it can listen on another address only when a flag says so, for the smoke-test container).

- `server/stand_in/src/modelhub_stand_in/store.py` - repositories, versions, files, checksums, the invented layouts (flat, nested).
- `rules.py`, `switches.py` - naming rules, 409 when a version exists without overwrite permission, size limits, and switches that make it fail on purpose.
- `app.py` - the calls `jf hf upload` and `huggingface_hub` make, listing, checksums, deletion.
- `server.py`, `__main__.py` - the `StandIn` context manager on a free local port (local only unless explicitly allowed) and the command line.
- `assumptions.json`, `register.py` - every behaviour it assumes, with the check to run on a real Artifactory.

## Key decisions

- Two invented layouts stand in for the real one, which is not documented; the import service's gateway discovers the layout by listing and depends on neither.
- It binds 127.0.0.1 only and takes its token from the caller; the only exception is the smoke-test container, switched on by an explicit flag.
- Tests use `write_bytes` so checksums match on Windows (a Windows CI failure found this).

## Test coverage summary

86 tests (`server/stand_in/tests/`): rules, switches and register, and integration tests with the real `huggingface_hub` client. Run on Linux in the server job and on Windows and macOS in the `stand-in` job. Re-run for this replay: 86 passed.

## Deviations from the plan

None for the unit itself. This record was written afterwards, in a replay through the engine; the unit was built earlier without it (see the stage diary).
