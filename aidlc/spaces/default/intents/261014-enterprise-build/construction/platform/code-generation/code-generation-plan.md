# Code Generation Plan: platform

## Summary

- Builds: how the server stack is packaged and run (images, Compose file, proxy, operator guide), the signed server pack, the whole-stack check and the Docker smoke test with the upgrade-and-return rehearsal, already built and merged in PRs #16 and #19, now reopened by Build and Test to close one Not Met target (no JFrog CLI in the import service image); this plan replays the unit through the workflow, adds that fix and checks it
- Touches: `deploy/`, `src/modelhub/serverpack.py` and the `pack` commands in `cli.py`, `.github/workflows/ci.yml`, `.dockerignore`, `server/e2e/`, the loop guard in `.claude/loop/` with its test and the working-agreement doc
- Tests: 52 pytest tests on the deployment files, the pack tools (with a stubbed `docker`) and the loop guard, the whole-stack check on real ports, and the CI `images` job (image build, scan, smoke test, rehearsal)

## Steps

- [ ] Step 1. Project structure and production configuration: `deploy/Dockerfile` (one recipe for the three services, non-root), `deploy/proxy/` (TLS, routing, JSON log), `deploy/compose.yaml`, `deploy/env.example`. (FR6.1, FR6.4, FR6.5, NFR5)
- [ ] Step 2. Verify the test runner and record the unit-scoped command: `.venv/bin/python -m pytest tests/test_deploy_definition.py tests/test_build_pack.py tests/test_serverpack.py -q`. (NFR9)
- [ ] Step 3. Business logic - Red, Green, Refactor: the signed server pack (`modelhub pack sign|verify`, `build-pack.sh`, `ops.sh load-images`). (FR6.2)
- [ ] Step 4. API / endpoint - Red, Green, Refactor: the operator script and guide: preflight, secrets, first install, upgrade and return. (FR6.6)
- [ ] Step 5. Integration - Red, Green, Refactor: the whole-stack check on real ports (`server/e2e`) and the sign-in stand-in server. (NFR1, AC4.2)
- [ ] Step 6. Environment/build configuration: the CI `images` job (build, stand-in absence, secret and user checks, scan, smoke test, rehearsal) and the `server-pack` job. (FR6.3, FR6.6, NFR5)
- [ ] Step 7. Workflow tooling: the loop guard hook, status line and working agreement that keep work on the AI-DLC loop. (process)
- [ ] Step 8. Documentation and traceability: `deploy/README.md`, `docs/traceability.md`. (NFR9)
- [ ] Step 9. Loop-back 1 (Build and Test, target artifactory-service NFR10.1, image side), Red then Green then Refactor: the import service image carries a pinned JFrog CLI (`jf`), downloaded on the internet side at build time from JFrog's release site for the image's CPU type and checked against a pinned SHA-256; the other images do not get it; the CLI's update check and usage reporting are switched off in the image; the default upload path stays `huggingface_hub`. A check of the Dockerfile and the CI image job (`jf --version` in the image) prove it. (NFR10.1, NFR8.1)
- [x] Step 10. Loop-back 2 (Build and Test, platform NFR5.1), Red then Green then Refactor: a log search `deploy/smoke/check_logs.py` that reads the logs of every container and fails if any secret value (every file under the secrets folder, plus the pack signing key material) appears in them, tested with sample logs that hold and do not hold a secret; the Docker smoke test in CI runs it after the rehearsal. Stays Unverified and named: NFR8.1 containers without a route to the internet (a host firewall matter, Compose cannot enforce it because the containers must reach Artifactory and Keycloak) and NFR7.2 free space also checked at start (a change in artifactory-service, left for the person to decide). No target is weakened. (NFR5.1)

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
