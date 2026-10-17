# Code Generation Plan: enterprise ModelHub (overall)

This is the plan for the whole build. The code goes to the workspace (`server/`, `web/`, `src/modelhub/`, `packaging/`, `.github/`), never to this record folder. After this plan is approved the build goes unit by unit, each unit with its own short plan that follows the same test-first order and the same contract below.

Inputs: the approved design `aidlc/spaces/default/intents/261011-enterprise-modelhub/` (read `architecture-overview.md` first), `inception/requirements-analysis/requirements.md` (this intent), `inception/units-generation/` (this intent).

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

## Build Order (walking skeleton first)

Each row is one pull request, squash-merged after all checks pass and your say-so. Each slice is written test first. Slice 0 is shared set-up.

- [x] Step 1. **PR 0, project set-up.** Create `server/` (packages `common`, `catalog`, `artifactory_service`, `stand_in`), a root test and lint command that covers `server/`, `web/` and `src/`; add the PostgreSQL test fixture (throwaway PostgreSQL 16 container via the Docker command line, skipped with a clear message when Docker is missing); add the fake token issuer helper; add the CI job and PostgreSQL service container. Record the unit-scoped test commands in `unit-test-instructions.md`.
- [x] Step 2. **PR 1, skeleton: `common`.** Token check (RS256/ES256, issuer, audience, expiry, key set with last-good keys and the 60 second refresh limit), request guard (default deny, open health paths), secrets loader, settings loader, JSON logging with redaction, health and ready helpers. Rules BR1.1 to BR1.12 of `common`.
- [x] Step 3. **PR 2, skeleton: `artifactory-stand-in`.** Upload calls (create, pre-upload, large-file batch, commit), tree and file listing, delete, token check, name rules, 409 on overwrite, partial-until-commit, two layouts, failure switches, call record, assumption register. Rules BR1.1 to BR1.16 of the stand-in (the skeleton needs the first group; the rest follow in a widening PR).
- [x] Step 4. **PR 3, skeleton: `catalog`.** Schema and migrations, store a version with files, documents, trail row and summary row in one transaction, identical-repeat and conflict, models list with filters, sort and paging, document read, personal-token make and introspect. Rules BR1.1 to BR1.9, BR1.13 to BR1.16, BR1.21 first.
- [x] Step 5. **PR 4, skeleton: `artifactory-service`.** Create import, pieces, start, verify and unpack, full import with the stand-in, record through the Catalog, job state, per-model lock, progress. Rules BR1.1 to BR1.9, BR1.11, BR1.12, BR1.19 first.
- [x] Step 6. **PR 5, skeleton: `portal`.** Sign-in with Keycloak (stood-in), session, the models list backed by the Catalog, model page basics, the token page. Rules BR1.1 to BR1.6, BR1.10, BR1.12 first.
- [x] Step 7. **PR 6, skeleton: `import-cli`.** `login`, `logout` and `import` of one bundle with verify, create, send pieces, start, watch, report and exit status. Rules BR1.1 to BR1.6, BR1.9 first.
- [x] Step 8. **Whole-stack check on the skeleton.** A script that starts the pieces with the stand-ins and imports a small bundle, then reads it in the portal list (the first end-to-end proof).
- [x] Step 9. **Widening PRs**, one per unit in dependency order (`catalog`, `artifactory-service`, `portal`, `import-cli`, `artifactory-stand-in`): the remaining rules, quality targets and error paths of each unit's approved design.
- [x] Step 10. **PR: `platform`.** Dockerfiles, Compose file, proxy configuration, secrets and database set-up script, health checks, image build, scan and server-pack steps in the release workflow, the whole-stack smoke test, the upgrade-and-return rehearsal.
- [x] Step 11. Documentation and traceability: README sections for the server and the new CLI commands, a requirement-to-test table.

## Test Files (mandatory, test first)

Each unit's tests live next to it (`server/<unit>/tests/`, `web/tests/`, `tests/`). Per component: five to eight unit tests plus integration tests at the key boundaries (database, token check, stand-in), as the standard strategy requires. Every test names the requirement or rule ID it checks. The existing 369 CLI tests and 24 portal tests stay green.

## Traceability

Requirement groups map to units as in `inception/units-generation/unit-of-work-story-map.md`; each unit's own plan lists its rule IDs (BR) as plan steps, and the per-unit `traceability.json` ties them to tests.
