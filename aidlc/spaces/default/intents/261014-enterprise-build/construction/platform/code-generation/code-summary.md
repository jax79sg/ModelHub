# Code Summary: platform

## What was built

How the server stack is packaged and run, built and merged before this replay (PRs #16 and #19), with workflow tooling added in PR #20.

- `deploy/Dockerfile`, `deploy/proxy/`, `deploy/compose.yaml`, `deploy/env.example`, `deploy/ops.sh`, `deploy/README.md` - one image recipe for the three services (non-root, no stand-in), the TLS proxy (only the web pages and the import calls are routed), the five-container Compose file (file-backed secrets, least privilege, health-ordered start, two separate volumes), the operator script and guide.
- `src/modelhub/serverpack.py`, `deploy/build-pack.sh`, `ops.sh load-images` - the signed server pack (`modelhub pack sign|verify`).
- `server/e2e` - the whole-stack check on real ports; `deploy/smoke/` - the Docker smoke test and the upgrade-and-return rehearsal, run by the CI `images` job.
- `.github/workflows/ci.yml` - image build, scan, checks and the signed-pack job; `.claude/loop/` and `docs/ai-dlc-working-agreement.md` - the loop guard and working agreement; `docs/traceability.md` - the requirement-to-test table.

## Key decisions

- Services run as a limited database role; a separate migration role makes the tables (added to the Catalog and import service start-up).
- Images disable Xet transfers and telemetry; the proxy applies the base image's operating-system fixes so the scan passes.
- The rehearsal leaves the stand-ins for outside systems running while the product is upgraded, as a real Artifactory would.

## Test coverage summary

Re-run for this replay: the deployment, pack and loop-guard tests pass; the whole-stack check passed at the stand-in checkpoint; the Docker parts ran green in CI (`images` job).

## Deviations from the plan

The upgrade-and-return rehearsal retags the same images as the new release, so it shows the procedure and data survival but not a schema change. This record was also written afterwards, in a replay through the engine; the unit was built earlier without it (see the stage diary).
