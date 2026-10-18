# CI Configuration

## Summary

CI is GitHub Actions: `.github/workflows/ci.yml` on every pull request to `main` and every push to `main`, and `.github/workflows/release.yml` for the command-line programs. It already existed and was extended during Build and Test; this stage records it, confirms it enforces the commands Build and Test recorded, and names what is still not enforced (merge gating, in `quality-gates.md`).

## Sources

- `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `.github/dependabot.yml`
- `construction/build-and-test/build-and-test-summary.md` and `test-results.md`
- `team.md` (trunk-based, squash merge, `ruff` line length 100, deployment as signed files carried by hand)
- `ci-pipeline-questions.md` (answers 1, 2 and 4)

## Branch strategy

Trunk-based: short branches into `main`, each squash-merged. Tags or releases carry versions; there are no long-lived branches.

## Jobs (all in `ci.yml`)

| Job | Runs | What it enforces |
|---|---|---|
| `lint` | `ruff check .`, `ruff format --check .` | Code style (line length 100) |
| `test` | `pytest -v --timeout=240` on Linux, Windows, macOS, Python 3.10 and 3.12 | The command-line program and its import command |
| `build-linux`, `run-linux-on-ubuntu-20-04`, `build-windows`, `build-macos` | Build the program (PyInstaller) and drive it through the whole workflow | The delivered programs work on each system |
| `offline-pack` | Build the offline pack on Linux and Windows | The air-gap pack |
| `web` | The prototype web app tests on three systems | The web prototype |
| `server` | Each server unit on real PostgreSQL: common, catalog, import service, portal, whole stack, stand-in, test helpers (Python 3.10 and 3.12) | The server units and the whole-stack path |
| `browser (chrome)` | Playwright drives the runner's Chrome through the real portal | Portal NFR10.1 (current Chrome) |
| `stand-in` | The Artifactory stand-in on Windows and macOS | The stand-in runs where the import command is tested |
| `images` | Builds the four images, checks them (no stand-in or test helpers, non-root, no secrets, JFrog CLI only in the import service image), scans with Trivy, runs the whole-stack smoke test and the upgrade-and-return rehearsal on a network with no route out, and searches every container's logs for secrets | Server packaging and deployment definition |
| `server-pack` | Builds and signs the server pack on pushes to `main` only (keys from repository secrets) | The thing carried across the air gap |
| CodeQL (`Analyze`) | Code scanning | Static security findings |
| `.github/dependabot.yml` | Weekly updates for Python packages, workflows and the image recipe | Dependencies (needs Dependabot switched on in repository settings) |

## Build and test commands the pipeline runs

These are the commands Build and Test recorded; each appears in a job above: `ruff check .`, `ruff format --check .`, `pytest` (root, `web`, and per server unit: common, catalog, artifactory_service, portal, e2e, stand_in, testkit), the image build and `deploy/smoke/run.sh`.

## Artifact repository

None. The server pack (signed images, compose file, guide, monitoring files) is produced by `server-pack` and carried by hand across the air gap after the content scan; the command-line programs are released by `release.yml`.

## Secrets used by CI

`PACK_KEY_ID`, `PACK_KEY_PRIVATE_B64`, `PACK_KEY_PUBLIC_B64` (repository secrets, owner to provide; used only by `server-pack`). No other secret is needed; image checks use generated values.

## Assumptions & Open Questions

- Branch protection on `main` is not yet set: the access token the tools use cannot change it. The person sets it (see `quality-gates.md`).
- The three signing secrets are not yet provided, so `server-pack` cannot sign until they are.
- GitGuardian can fail on test fixtures that look like keys; the one raised so far (incident 38341728) was marked a false positive by the person.
