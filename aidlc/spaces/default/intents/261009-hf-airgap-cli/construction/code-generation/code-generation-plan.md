# Code Generation Plan

## Summary

- Builds: the full `modelhub` tool from `requirements.md` and `contract-summary.md`: `pull`, `bundle`, `verify`, `unpack`, `list` and a `key` command group, with signing, README pictures, file-type choice, splitting into pieces, progress display, and packaging definitions for a single program file per system.
- Touches: `src/modelhub/` (existing modules reworked in place, new modules added), `tests/` (new test files plus fixtures), `pyproject.toml`, `packaging/`, `README.md`.
- Tests: about 100 automated tests (roughly 5 to 8 per component) plus about 12 end-to-end tests for the key boundaries, all written before the code they test.

## Testing Contract

```json
{
  "version": 1,
  "methodology": "tdd",
  "source": "team",
  "ordering": "Write a failing test for each behaviour first, then the code that makes it pass, then tidy up.",
  "scope": "security-patch",
  "test_strategy": "standard",
  "project_type": "brownfield",
  "applicable_notes": [
    {
      "layer": "org",
      "text": "We treat tests as a first-class deliverable in every Bolt. The specific\nmethodology (TDD, BDD, ATDD, or classic test-after) is affirmed at\npractices-discovery and recorded in `team.md` under this heading with explicit\n`Methodology` and `Ordering` fields; Code Generation resolves those fields\nindependently from coverage, tooling, and scope notes.\n\nWhen no posture has been affirmed, our default per scope is:\n- **Methodology**: test-after\n- **Ordering**: implement each applicable testable layer, then write and run\n  that layer's tests.\n- `mvp`, `enterprise`, `feature`, `infra`, `classic` add an 80% line-coverage\n  floor and CI execution before merge.\n- `bugfix`, `security-patch` add a targeted regression for the specific\n  bug/vulnerability and require the existing suite to remain green.\n- `express` uses the Minimal strategy: requirement-driven unit tests (one per\n  requirement, with a happy-path floor per component); existing tests remain\n  green.\n- `poc`, `refactor`, `workshop` add no extra new-test floor and require the\n  existing suite to remain green.\n\nThe active `Test Strategy` still applies in every scope and determines test\nvolume/types. Scope floors are additive; they never reduce or replace the\nselected strategy.\n\nBuild and Test verifies defined coverage floors and affirmed quality targets;\nthey may not be weakened to make a step pass.\n\nAffirm a stricter posture in `team.md` if the team commits to one."
    },
    {
      "layer": "team",
      "text": "- **Methodology**: tdd\n- **Methodology evidence**: chosen in the interview (Q4); the existing prototype's tests were written after the code, so this is a change of habit for new work.\n- **Ordering**: Write a failing test for each behaviour first, then the code that makes it pass, then tidy up.\n- Every change has a test for it, and the existing tests keep passing. There is no percentage coverage floor.\n- The test tool is `pytest`; tests live in `tests/`."
    }
  ],
  "obligations": {
    "strategy": "standard",
    "strategy_volume": [
      "Five to eight tests per component.",
      "Unit tests plus integration tests for key boundaries.",
      "Add E2E, performance, or security tests when requirements demand them."
    ],
    "scope_floor": [
      "Include a targeted regression for the bug or vulnerability.",
      "Keep the existing test suite green."
    ],
    "combination_rule": "Apply every selected-strategy obligation and every scope-floor obligation; neither replaces the other, and a targeted scope regression may add the narrowest necessary test type beyond the strategy default."
  },
  "plan_profile": {
    "methodology": "tdd",
    "runner_step": "Verify the existing test runner/configuration and record the exact unit-scoped command.",
    "runner_ready_before_first_test": true,
    "testable_layers": [
      "Data model / database behavior",
      "Repository / data access",
      "Business logic",
      "API / endpoint",
      "Frontend behavior"
    ],
    "steps": [
      "Project structure and production configuration skeleton.",
      "Verify the existing test runner/configuration and record the exact unit-scoped command.",
      "Data model / database behavior - Red: write the failing tests and record the failing command output.",
      "Data model / database behavior - Green: implement only enough behavior to pass.",
      "Data model / database behavior - Refactor: improve the implementation while tests stay green.",
      "Repository / data access - Red: write the failing tests and record the failing command output.",
      "Repository / data access - Green: implement only enough behavior to pass.",
      "Repository / data access - Refactor: improve the implementation while tests stay green.",
      "Business logic - Red: write the failing tests and record the failing command output.",
      "Business logic - Green: implement only enough behavior to pass.",
      "Business logic - Refactor: improve the implementation while tests stay green.",
      "API / endpoint - Red: write the failing tests and record the failing command output.",
      "API / endpoint - Green: implement only enough behavior to pass.",
      "API / endpoint - Refactor: improve the implementation while tests stay green.",
      "Frontend behavior - Red: write the failing tests and record the failing command output.",
      "Frontend behavior - Green: implement only enough behavior to pass.",
      "Frontend behavior - Refactor: improve the implementation while tests stay green.",
      "Environment/build configuration.",
      "Documentation and traceability."
    ]
  },
  "input_sha256": "sha256:74cb90d8c82852a6938408f1d869e028e0ab68a228ae433315543b5c3e16a35a",
  "contract_sha256": "sha256:778ca50cce5e2cadd57905c5678a7b9273f647cf3409377bf438f7a0d3a477a2"
}
```

## How The Layers Map To This Tool

- Data model: the file formats in `contract-summary.md` (C1 record, C2 bundle manifest, C3 summary and store layout) as code that reads, writes and validates them.
- Repository / data access: the Hugging Face client (behind a small interface so a fake can stand in), the on-disk store and record writers, the piece reader and writer.
- Business logic: file-type grouping, slicing and joining, signing and trust, checking, rebuilding, retries, progress.
- API / endpoint: the command line (`cli.py`): commands, options, exit status.
- Frontend: not applicable. The web app is out of scope.

The tool is built as thin slices, each from test to code, as `team-practices` requires: slice L1 first, the whole way through, then L2 onward.

## Plan Steps

- [x] Step 1: Project structure and configuration: add the `cryptography` dependency and a `network` test marker to `pyproject.toml`; create module files (empty) for `filetypes`, `hubclient`, `record`, `summary`, `readme_assets`, `download`, `pieces`, `bundle`, `signing`, `verify`, `unpack`, `store`, `progress`, `runrecord`, `fsutil`; add `tests/fixtures/`. Requirements: FR8.4, NFR8.2.
- [x] Step 2: Verify the existing test runner: run `pytest tests/test_cli.py tests/test_airgap_roundtrip.py` and record the exact commands in `unit-test-instructions.md`. The existing tests must stay green or be replaced on purpose by L1 where the contract changed.
- [x] Step 3 (L1 Red): Thin end-to-end slice, failing tests first: against a fake Hub, `pull` writes a C1 record for a tiny model; `key create`, `bundle` (one piece, signed), `key trust`, `verify`, `unpack`, `list` run the whole way through and the listed model matches. Tests: `tests/test_slice_roundtrip.py`, `tests/test_record.py`, `tests/test_fsutil.py`. Requirements: FR1.1, FR3.1, FR3.3, FR5.4, FR6.1, FR7.1 to FR7.4, NFR2.1 to NFR2.4.
- [x] Step 4 (L1 Green): Implement `fsutil` (atomic write, streaming SHA-256), `hubclient` (interface plus fake), `record`, `signing` (Ed25519 key create, sign, verify), `bundle`, `pieces`, `verify`, `unpack`, `store`, and the commands, only as far as the slice needs.
- [x] Step 5 (L1 Refactor): Tidy names and module boundaries while the slice stays green; run `ruff`.
- [x] Step 6 (L2 Red): File types and selection tests: grouping by type with sizes and explanations; select by type; no selection shows the list and downloads nothing; a list-file run applies one selection to all; small settings files and the README are always fetched. Tests: `tests/test_filetypes.py`, `tests/test_pull_selection.py`. Requirements: FR2.1 to FR2.5, FR1.2.
- [x] Step 7 (L2 Green): Implement `filetypes` and the selection flow in `pull`.
- [x] Step 8 (L2 Refactor): Tidy and keep green.
- [x] Step 9 (L3 Red): Model-page data tests: README and header, summary details, file list with checksums and scan results, history and refs, raw responses kept as returned, capture time, `null` for unknown values, licence file and the "licence text not available" record. Tests: `tests/test_summary.py`, `tests/test_pull_metadata.py`. Requirements: FR3.1 to FR3.6, FR1.3, FR1.4.
- [x] Step 10 (L3 Green): Implement `summary` and the metadata capture in `pull`; private and gated models are reported and skipped.
- [x] Step 11 (L3 Refactor): Tidy and keep green.
- [x] Step 12 (L4 Red): README picture tests: find pictures; fetch outside pictures; write `README.local.md` with local paths and keep the original; failed picture listed and left unchanged; only `http` and `https`; 7 MB limit; 30-second time limit. Tests: `tests/test_readme_assets.py`. Requirements: FR4.1 to FR4.4, NFR5.3.
- [x] Step 13 (L4 Green): Implement `readme_assets`.
- [x] Step 14 (L4 Refactor): Tidy and keep green.
- [x] Step 15 (L5 Red): Download robustness tests: retry 5 times with 1, 2, 4, 8, 16 second waits and jitter; rate-limit wait from the server's guidance; 8 files at once by default and adjustable; resume skips completed files; checksum mismatch marks a file failed; token only from environment or a hidden prompt, never in output. Tests: `tests/test_download.py`, `tests/test_token.py`. Requirements: FR5.1 to FR5.5, NFR1.2, NFR3.2, NFR3.5, NFR6.1, NFR6.2, NFR6.3.
- [x] Step 16 (L5 Green): Implement `download` over the official library's fast route, with the fake Hub for tests.
- [x] Step 17 (L5 Refactor): Tidy and keep green.
- [x] Step 18 (L6 Red): Splitting tests: piece size set by the user; interactive drive-by-drive mode; piece size below 1 GB; pieces are plain slices of one tar stream that join by hand; piece checksums and names; atomic piece writes; free-space check before writing; run lock; Windows-unwritable names reported, never renamed. Tests: `tests/test_pieces.py`, `tests/test_bundle_split.py`, `tests/test_interactive_drives.py`, `tests/test_locking.py`. Requirements: FR6.1 to FR6.8, NFR3.3, NFR3.6, NFR3.7, NFR3.8, NFR7.5.
- [x] Step 19 (L6 Green): Implement slicing, interactive mode, free-space check, lock and name checks in `bundle`, `pieces`, `fsutil`.
- [x] Step 20 (L6 Refactor): Tidy and keep green.
- [x] Step 21 (L7 Red): Air-gapped side tests: missing and damaged pieces all named in one run; pieces from several drives in any order; replace one piece without touching others; resumable rebuild; rebuilt file failing its checksum is removed; archive entries that escape the folder, absolute paths and links outside are refused; stream longer than declared stops; `list` fields; case-collision detection. Tests: `tests/test_verify.py`, `tests/test_unpack.py`, `tests/test_unpack_safety.py`, `tests/test_list.py`. Requirements: FR7.1 to FR7.5, NFR2.10, NFR3.4, NFR4.1 to NFR4.4, NFR7.6.
- [x] Step 22 (L7 Green): Implement `verify`, `unpack` and `store` changes.
- [x] Step 23 (L7 Refactor): Tidy and keep green.
- [x] Step 24 (L8 Red): Signing lifecycle tests (the targeted regression for tampering): one byte changed in a piece, a file, the manifest or the signature is caught; missing signature, bad signature and unknown key each refuse with their own message; fingerprint is the same for the same key; trust needs a typed confirmation; a key inside a bundle is not trusted; owner-only private key file; the private key and a fake token never appear in outputs. Tests: `tests/test_signing.py`, `tests/test_trust.py`, `tests/test_tamper_regression.py`, `tests/test_secrets.py`. Requirements: NFR2.1 to NFR2.9, NFR6.1, NFR6.4.
- [x] Step 25 (L8 Green): Implement the `key` command group and the signature checks in `verify` and `unpack`.
- [x] Step 26 (L8 Refactor): Tidy and keep green.
- [x] Step 27 (L9 Red): Progress, run record and exit status tests: progress shown at least every 2 seconds on a terminal and a line every 30 seconds otherwise; three detail levels with a log file; the run record lists fetched, skipped and failed items with sizes, timings, retries, tool version and platform; exit statuses 0, 1 and 2. Tests: `tests/test_progress.py`, `tests/test_runrecord.py`, `tests/test_exit_status.py`. Requirements: NFR1.5, NFR8.3 to NFR8.5, FR9.1, FR9.2, FR8.3.
- [x] Step 28 (L9 Green): Implement `progress`, `runrecord`, log levels and exit statuses in the commands.
- [x] Step 29 (L9 Refactor): Tidy and keep green.
- [x] Step 30 (L10 Red): Memory, scale and offline tests: checking a 2 GB file under a 256 MB memory limit; a 500 GB sparse file within 8 GB; a 1 TB sparse file through bundle, verify and unpack; 999,999 pieces accepted and 1,000,000 refused; `list` of 10,000 version folders in 5 seconds; verify time independent of store size; the offline commands run with all network blocked; stop at every write point and restart gives a correct result. Tests: `tests/test_memory_limits.py`, `tests/test_scale.py`, `tests/test_offline.py`, `tests/test_kill_restart.py`. Requirements: NFR1.3, NFR1.4, NFR1.7 to NFR1.11, NFR3.1, NFR5.1, NFR5.2.
- [x] Step 31 (L10 Green): Make the implementation stream in blocks everywhere, add the network guard used by the tests, and fix whatever the tests find.
- [x] Step 32 (L10 Refactor): Tidy and keep green.
- [x] Step 33 (L11 Red): Packaging tests: the version command output; a script check that the build definitions list the native parts (`hf_xet`, `cryptography`) and the entry point; platform text rules (UTF-8, byte-order mark, Windows line endings, long paths). Tests: `tests/test_packaging_defs.py`, `tests/test_text_encoding.py`. Requirements: FR8.1 to FR8.3, NFR7.4.
- [x] Step 34 (L11 Green): Add `packaging/pyinstaller.spec`, `packaging/nuitka.cfg` and `packaging/build.py` for the test build described in `tech-stack-decisions.md` (T8). The builds themselves run in the check step on Linux and Windows, not here.
- [x] Step 35 (L11 Refactor): Tidy and keep green.
- [x] Step 36: Environment and build configuration: final `pyproject.toml` (entry point, dependencies, `ruff`, `pytest` markers), `.gitignore` additions for build output.
- [x] Step 37: Documentation and traceability: update `README.md` (install, the workflow from download to air-gapped store, key trust, recovering by hand), write `code-summary.md` and `traceability.json`.

## Requirement Traceability

| Plan steps | Requirements covered |
|------------|----------------------|
| 3 to 5 | FR1.1, FR3.1, FR3.3, FR5.4, FR6.1, FR7.1 to FR7.4, NFR2.1 to NFR2.4 |
| 6 to 8 | FR1.2, FR2.1 to FR2.5 |
| 9 to 11 | FR1.3, FR1.4, FR3.1 to FR3.6 |
| 12 to 14 | FR4.1 to FR4.4, NFR5.3 |
| 15 to 17 | FR5.1 to FR5.5, NFR1.2, NFR3.2, NFR3.5, NFR6.1 to NFR6.3 |
| 18 to 20 | FR6.1 to FR6.8, NFR3.3, NFR3.6 to NFR3.8, NFR7.5 |
| 21 to 23 | FR7.1 to FR7.5, NFR2.10, NFR3.4, NFR4.1 to NFR4.4, NFR7.6 |
| 24 to 26 | NFR2.1 to NFR2.9, NFR6.1, NFR6.4 |
| 27 to 29 | FR8.3, FR9.1, FR9.2, NFR1.5, NFR8.3 to NFR8.5 |
| 30 to 32 | NFR1.3, NFR1.4, NFR1.7 to NFR1.11, NFR3.1, NFR5.1, NFR5.2 |
| 33 to 35 | FR8.1, FR8.2, FR8.3, FR8.4, NFR7.1 to NFR7.4 |
| 36, 37 | NFR7.3, NFR8.1, NFR8.2 |

Requirements that no code step can finish alone are measured later or elsewhere: NFR1.1 (80% of connection speed) is a benchmark on your connection, NFR7.1 and NFR7.2 (the program file running on the listed systems) and NFR7.3 (tests on both systems) are proven by the check step on Linux and Windows, and the packaging choice T8 is decided there.

## Assumptions In This Plan

- The Hugging Face client is wrapped in a small interface so a fake can stand in during tests; real-network tests carry the `network` marker and run only on request.
- The signature scheme is Ed25519 through `cryptography`, as provisional decision T7; if it cannot be packaged, the plan changes before step 25.
- Existing prototype tests in `tests/test_airgap_roundtrip.py` are replaced deliberately in step 3 where the contract changed (single tar with a manifest becomes C1 to C3), and the rest keep passing.
