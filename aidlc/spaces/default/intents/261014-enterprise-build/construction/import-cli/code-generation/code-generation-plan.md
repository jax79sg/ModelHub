# Code Generation Plan: import-cli

## Summary

- Builds: `modelhub login`, `logout` and `import` (verify here, send to the import service piece by piece, report each model), already built and merged in PR #15; this plan replays the unit through the workflow and checks it
- Touches: `src/modelhub/importer.py`, `settings.py`, `cli.py`, a small option in `verify.py`, `tests/test_import_cli.py`, `tests/fake_import_service.py`, the README and the `httpx` dependency
- Tests: 29 new pytest tests against a fake import service, plus an end-to-end test of this client against the real service (in the artifactory-service unit); the existing CLI tests stay green

## Steps

- [x] Step 1. Project structure and production configuration: `httpx` as a direct dependency, `importer.py` and `settings.py` modules. (NFR10)
- [x] Step 2. Verify the test runner and record the unit-scoped command: `.venv/bin/python -m pytest tests/test_import_cli.py -q`. (NFR9)
- [x] Step 3. Business logic - Red, Green, Refactor: saved settings (private file, https or local http only, token typed with no echo, never printed), environment overrides. (FR1.2, FR1.11)
- [x] Step 4. Business logic - Red, Green, Refactor: find bundles, verify here first, create, send only the missing pieces one at a time with their checksum, start, watch, report each model and the exit status. (FR1.1, FR1.4, FR1.10, FR1.11)
- [x] Step 5. Business logic - Red, Green, Refactor: retries 1, 2, 4, 8, 16 s with jitter, no retry for answers that cannot improve, busy waiting up to 30 minutes, 401 and 426 stop the run, Ctrl-C leaves the import to resume. (FR1.9, FR1.12, NFR4)
- [x] Step 6. API / endpoint - Red, Green, Refactor: the commands `login`, `logout`, `import` (with `--from-store` reserved) and the refusal of a token option. (FR8.1, FR1.2)
- [x] Step 7. Environment/build configuration: runs on Linux, Windows and macOS in CI. (NFR10)
- [x] Step 8. Documentation and traceability: the README section on login, import and logout. (FR1.13)

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
