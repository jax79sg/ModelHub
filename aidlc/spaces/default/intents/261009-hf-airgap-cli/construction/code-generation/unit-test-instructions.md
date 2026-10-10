# Unit Test Instructions

How to run and write the tests for this piece of work. Testing approach: test-driven (`team-practices`); strategy: standard; plan: `code-generation-plan.md`.

## Test Framework And Setup

- Tool: `pytest` (already in the `dev` extras). Tests live in `tests/`.
- One-time setup in the project folder:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

- On Windows the same steps use `.venv\Scripts\pip` and `.venv\Scripts\pytest`.
- Checks: `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`

## Runnable Command Before The First Test (plan step 2)

```bash
.venv/bin/pytest tests/test_cli.py tests/test_airgap_roundtrip.py
```

This is the exact existing-suite command. Plan step 2 runs it to confirm it passes before any code changes; it could not be run earlier because commands wait for plan approval. All commands below name exact test files, never the whole project.

## Commands By Component

| Slice | Component | Command |
|-------|-----------|---------|
| L1 | End-to-end slice, record, file helpers | `.venv/bin/pytest tests/test_slice_roundtrip.py tests/test_record.py tests/test_fsutil.py` |
| L2 | File types and selection | `.venv/bin/pytest tests/test_filetypes.py tests/test_pull_selection.py` |
| L3 | Model-page data | `.venv/bin/pytest tests/test_summary.py tests/test_pull_metadata.py` |
| L4 | README pictures | `.venv/bin/pytest tests/test_readme_assets.py` |
| L5 | Download robustness, token | `.venv/bin/pytest tests/test_download.py tests/test_token.py` |
| L6 | Splitting, drives, locking | `.venv/bin/pytest tests/test_pieces.py tests/test_bundle_split.py tests/test_interactive_drives.py tests/test_locking.py` |
| L7 | Air-gapped side | `.venv/bin/pytest tests/test_verify.py tests/test_unpack.py tests/test_unpack_safety.py tests/test_list.py` |
| L8 | Signing and tamper regression | `.venv/bin/pytest tests/test_signing.py tests/test_trust.py tests/test_tamper_regression.py tests/test_secrets.py` |
| L9 | Progress, run record, exit status | `.venv/bin/pytest tests/test_progress.py tests/test_runrecord.py tests/test_exit_status.py` |
| L10 | Memory, scale, offline, restart | `.venv/bin/pytest tests/test_memory_limits.py tests/test_scale.py tests/test_offline.py tests/test_kill_restart.py` |
| L11 | Packaging definitions, text rules | `.venv/bin/pytest tests/test_packaging_defs.py tests/test_text_encoding.py` |
| Existing | Prototype tests that stay green | `.venv/bin/pytest tests/test_cli.py tests/test_airgap_roundtrip.py` |

Real-network tests (marked `network`) run only on request:

```bash
.venv/bin/pytest -m network tests/test_download.py
```

## Test-First Rule For Every Step

For each behaviour, write the test, run its slice command, and see it fail for the right reason before writing the code. Record the failing output in the step's note in `code-summary.md`. Then write the least code that passes, then tidy up with the tests green.

## Expected Coverage

There is no percentage floor (`team-practices`). Each requirement row in `requirements.md` and the NFR documents has at least one named test; the table is written to `traceability.json`. Standard strategy: about 5 to 8 tests per component, plus end-to-end tests for these boundaries: pull to bundle (C1), bundle to unpack (C2), unpack to the folder the web app reads (C3), and the command line (C4).

## Targeted Regression (security-patch floor)

`tests/test_tamper_regression.py` changes one byte at a time in every kind of file and checks that `verify` always catches it, and refuses an unsigned or wrongly signed bundle. `tests/test_unpack_safety.py` proves archives cannot write outside the target folder.

## Mocking And Stubbing

- The Hugging Face client sits behind a small interface (`hubclient`). Tests use a fake that serves saved responses and file bytes from `tests/fixtures/`. A script `tests/tools/record_hub_fixtures.py` re-records a small public model's responses on request (needs the network).
- README pictures are served by a local test web server on `127.0.0.1` so no outside site is used.
- Time and waits (retries, progress) use an injectable clock so tests do not sleep.
- The network guard used by the offline tests replaces socket creation with an error.

## Test Data

- Large files are sparse files created in a temporary folder (`tmp_path`) so tests use almost no disk or time. The 500 GB and 1 TB cases check streaming and counts, not real content.
- Keys for tests are generated per test run; no real key is stored in the repository.
- Fake tokens use an obvious fake value so the secrecy tests can search for it.
