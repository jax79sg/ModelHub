# Code Generation Plan: artifactory-service

## Summary

- Builds: the import service (import jobs, the C1 import API, trusted keys, retention, the Artifactory gateway and Catalog client), already built and merged in PR #13 and widened in PR #20, now reopened by Build and Test to close two Not Met targets (degraded readiness, fixed event codes); this plan replays the unit through the workflow, adds those two fixes and checks it
- Touches: `server/artifactory_service/` (package `modelhub_artifactory_service`, numbered SQL step, tests in `server/artifactory_service/tests/`), and small hooks in `src/modelhub/` it reuses (`verify`, `unpack`, `signing`)
- Tests: 154 pytest tests on real PostgreSQL, the Artifactory stand-in and the real Catalog, including an end-to-end run of the program's own import client

## Steps

- [ ] Step 1. Project structure and production configuration: `server/artifactory_service/pyproject.toml`, package `modelhub_artifactory_service`. (NFR9)
- [ ] Step 2. Verify the test runner and record the unit-scoped command: `.venv/bin/python -m pytest server/artifactory_service -q`. (NFR9)
- [ ] Step 3. Data model / database - Red, Green, Refactor: the service's own schema (jobs, received pieces, model locks, trusted keys, retention), numbered step under a lock, the limited role. (FR1.12, FR1.14, FR5.1, NFR5)
- [ ] Step 4. Repository / data access - Red, Green, Refactor: the gateway (list a version with prefix discovery, delete, upload through `huggingface_hub` or `jf`, errors that never echo a credential) and the Catalog client with the service token. (FR1.6, FR1.8, FR1.9)
- [ ] Step 5. Business logic - Red, Green, Refactor: names, signature against trusted keys, disk check, per-model lock, the plan decision (skip, repair, finish, full), pieces consumed as read, upload with retries, record in the Catalog, cancel, idle and restart sweeps. (FR1.1 to FR1.14, FR2.1 to FR2.8)
- [ ] Step 6. Business logic - Red, Green, Refactor: retention (period, due list, keep, two-step removal) and trusted keys. (FR5.1 to FR5.7, FR4.2)
- [ ] Step 7. API / endpoint - Red, Green, Refactor: the C1 and C4 routes, personal-token check through the Catalog, the 426 rule, administrator-only changes. (FR1.2, FR4.3, FR4.5)
- [ ] Step 8. Start-up and environment: settings and secret files, migration role, idle sweep. (FR6.4, FR6.5)
- [ ] Step 9. Documentation and traceability: module docstrings naming the rules; the plan-decision deviation recorded in the code summary. (NFR9)
- [ ] Step 10. Loop-back 1 (Build and Test, targets artifactory-service NFR6.2 and NFR6.5), Red then Green then Refactor for (a) `/readyz` reporting Artifactory and the Catalog as degraded (never critical) and (b) the fixed event codes `import_created`, `import_skipped`, `import_done`, `import_failed`, `import_cancelled`, `key_added`, `key_revoked` and `retention_decided` logged with no secret, token or raw Artifactory output. (NFR6.2, NFR6.5)
- [x] Step 11. Loop-back 2 (Build and Test, Unverified targets that can be checked here), Red then Green then Refactor: tests for short calls at the 95th percentile under 1 second (NFR2.1) and with 20 callers at once (NFR7.7); per-piece overhead under 100 ms (NFR4.1); the service stopped at each state of an import and rerun with no half-finished result (NFR4.2); Artifactory or the Catalog down and back as a whole (NFR3.2); server memory with pieces and files streamed in blocks of at most 8 MiB on a large bundle (NFR7.3); the credential in no log and no process listing (NFR5.2); owner-only permission on the work folder (NFR5.5); no connection outside the machine (NFR8.1); exact pins for `jf` and `huggingface_hub` in the image (NFR9.2). Stays Unverified and named: alert thresholds (monitoring team), a 100 GB import and disk speed on a real Artifactory (NFR7.1, NFR7.2), free-space planning (NFR7.6), and the JFrog CLI download until CI builds the image (NFR10.1). No target is weakened.

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
