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

## Loop-back 2

Build and Test left nine stand-in targets Unverified; they are now checked by nine tests in `server/stand_in/tests/test_limits_and_hygiene.py`: start to first answer under 2 s (NFR9.1), 95th percentile of calls that move no content under 50 ms over 200 calls (NFR9.2), a 1 TiB declaration accepted with traced memory under 500 MB (NFR9.3), 1,000 stored versions of which one holds 10,000 files (NFR7.1; the target says "up to", so 1,000 versions of 10,000 files each, about 10 million files, was not tried), eight concurrent uploads to different versions without mix-up (NFR7.2), the token and file content in no call record and no log (NFR5.3), a token in the environment never used and no environment read in the source (NFR5.6), and a full round trip with every non-local connection refused (NFR8.1). The stand-in run on its own now logs one JSON line per call in the shared shape (ts, level, service, event, message, status), with no token or body (NFR6.1). No target was weakened.

## Deviations from the plan

None for the unit itself. This record was written afterwards, in a replay through the engine; the unit was built earlier without it (see the stage diary).
