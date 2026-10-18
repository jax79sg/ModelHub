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

## Loop-back 1 (from Build and Test)

Build and Test found the import service image lacked the JFrog CLI the design names (NFR10.1). `deploy/Dockerfile` now installs a pinned JFrog CLI (2.122.0, downloaded from JFrog's release site on the internet side for the image's CPU type and checked against a pinned SHA-256) into the import service image only; the CLI's update check and usage reporting are switched off and its home is on the writable temporary folder. The default upload path stays `huggingface_hub`. Four new checks in `tests/test_deploy_definition.py` cover the pinning, the unit restriction, the switches and the CI step; the CI image job runs `jf --version` in the service image and fails if `jf` is in any other image. Not proven until CI builds the image: the download and checksum step.

## Loop-back 2

Build and Test left platform NFR5.1 only partly proven (images and environment were searched in CI, the logs of the containers were not). `deploy/smoke/check_logs.py` now reads the logs of every container after the rehearsal and fails if any secret value appears in them (one-line secrets whole, keys line by line without BEGIN and END lines, values under 8 characters left out), naming only the secret's file; `deploy/smoke/run.sh` runs it before it reports success; six tests in `tests/test_smoke_logs.py` cover pass, fail, key lines, BEGIN lines, missing input and the wiring (CLI suite: 480 passed). The search itself runs in CI only, on a Docker host, so NFR5.1 is Met by tests of the search plus the CI step, and is proven end to end when CI runs. Still Unverified and named: NFR8.1 containers without a route to the internet (a host firewall matter; Compose cannot enforce it because the containers must reach Artifactory and Keycloak) and NFR7.2 free space also checked at start (the service checks at create; adding a check at start changes artifactory-service, left for the person to decide). No target was weakened.

## Loop-back 2

Loop-back 5 (Build and Test, the repository-side part of the remaining Unverified targets), all in `deploy/`. (a) `deploy/monitoring/error_rate.py` reads the JSON access lines of the services (a `docker compose logs` file works) and prints the share of 5xx lines per service, with `--fail-above`; `deploy/monitoring/alerts.json` lists the six alerts of the design with their thresholds, windows and the log, health or host signal each is read from; six tests in `server/common/tests/test_monitoring.py` run the tool on access lines really written by the shared guard and check that every signal the rules name exists (catalog NFR6.3; the rules for catalog NFR6.4 and import service NFR6.4). Both files go into the signed server pack (`build-pack.sh`, its test and the guide are updated). (b) `ops.sh preflight` now stops with a plain message when the Docker data folder has less than 540 GB free (100 GB database plus 440 GB import area), unless `MODELHUB_PREFLIGHT_SMALL=1` says it is a small test server; three tests with stubbed `docker` and `df` (catalog NFR7.2, import service NFR7.6). (c) The Docker smoke test and rehearsal run on a network with no route out (`internal: true`, nothing published) and `run.sh` checks that the catalog, portal, import service and proxy containers cannot reach the internet; static tests guard this and the proof is the CI images job (platform NFR8.1). Suites: CLI 486 passed, common 99 passed. Still Unverified and named: the alert thresholds being set in the monitoring system (catalog NFR6.4 and import service NFR6.4: the monitoring team loads `alerts.json`) and import service NFR9.2 (the person's decision and the real Artifactory). No target was weakened.

## Deviations from the plan

The upgrade-and-return rehearsal retags the same images as the new release, so it shows the procedure and data survival but not a schema change. This record was also written afterwards, in a replay through the engine; the unit was built earlier without it (see the stage diary).
