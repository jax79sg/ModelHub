# Code Generation Plan: artifactory-stand-in

## Summary

- Builds: the test-only imitation of Artifactory's Hugging Face repository (already built and merged in PR #11; this plan replays the unit through the workflow and checks it)
- Touches: `server/stand_in/` (package `modelhub_stand_in`, tests in `server/stand_in/tests/`), `.github/workflows/ci.yml` (Windows and macOS jobs)
- Tests: 86 pytest tests (unit and integration against the real `huggingface_hub` client), run on Linux, Windows and macOS

## Steps

- [ ] Step 1. Project structure and production configuration: `server/stand_in/pyproject.toml`, package `modelhub_stand_in`, entry `python -m modelhub_stand_in`. (FR7.1)
- [ ] Step 2. Verify the test runner and record the unit-scoped command: `.venv/bin/python -m pytest server/stand_in -q`. (NFR9)
- [ ] Step 3. Data model - Red, Green, Refactor: the in-memory store of repositories, versions, files and checksums, with the invented layouts (flat, nested). (FR7.1, FR7.2)
- [ ] Step 4. Business logic - Red, Green, Refactor: naming rules, 409 on an existing version without overwrite permission, revisions as commit hashes, size limits, the switches that make it fail on purpose. (FR7.2)
- [ ] Step 5. API / endpoint - Red, Green, Refactor: the calls `jf hf upload` and the `huggingface_hub` library make (create repository, pre-upload, commit, large-file batch), listing, checksums, deletion. (FR7.1)
- [ ] Step 6. Server wrapper and command line: `StandIn` context manager on a free local port, token from the caller, local-only unless explicitly allowed. (FR7.1)
- [ ] Step 7. Environment/build configuration: Windows and macOS CI jobs for this unit. (NFR10)
- [ ] Step 8. Documentation and traceability: `assumptions.json`, the register and its checklist for a real Artifactory. (FR7.2, FR7.3)
- [x] Step 9. Loop-back 2 (Build and Test, Unverified targets that can be checked here), Red then Green then Refactor: tests for start-to-first-answer time, 95th percentile of non-content calls, a 1 TiB virtual file within the memory limit, 1,000 versions of 10,000 files listed, 8 concurrent uploads, the token never in the call record or logs, the environment never read for the token, and no connection outside the machine; the stand-in logs in the shared JSON shape. No target is weakened. (NFR6.1, NFR9.1, NFR9.2, NFR9.3, NFR7.1, NFR7.2, NFR5.3, NFR5.6, NFR8.1)

## Testing Contract

```json
{
  "version": 1,
  "methodology": "tdd",
  "source": "team",
  "ordering": "Write a failing test for each behaviour first, then the code that makes it pass, then tidy up.",
  "scope": "classic",
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
      "Keep the existing test suite green.",
      "This scope adds no extra new-test floor beyond the selected test strategy."
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
  "input_sha256": "sha256:e72f6e8b7b13ff7bd01a65200613fc5e3ddce227476ba967420e141423aa4364",
  "contract_sha256": "sha256:55d36f92d3b092cd6743314534dc2dd04be5116b866766b965543059df476903"
}
```
