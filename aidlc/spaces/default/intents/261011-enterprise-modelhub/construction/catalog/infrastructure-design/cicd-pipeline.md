# CI/CD Pipeline: catalog

How the Catalog image is built, tested, scanned and upgraded, using the existing GitHub Actions pipeline on the internet side and the manual, rehearsed upgrade-and-return steps on the server.

## Steps

1. A pull request runs ruff, pytest against a real PostgreSQL started for the run, and the load script that fills 1,000 models and times 100 list requests (target: at least 95 under 1 second).
2. On merge to main the release workflow builds the Catalog image from python:3.12-slim with the shared library installed from the same commit, tags it with the release version, and scans it; a critical finding that has a fix fails the release.
3. The image and the PostgreSQL image are pushed to the internet-side registry and carried to the internal registry by digest as one reviewed batch (the manual step the team already uses for the offline packs).
4. Upgrade on the server: stop the stack, change the image tags in the Compose file, start; the Catalog applies its numbered database steps under a lock and keeps data.
5. Return: stop, put the previous tags back, start. The previous images stay in the registry and on the server. A database step that removed data is never released in the same version that stopped using it (two-release rule).
6. The upgrade-and-return is rehearsed once from an old to a new version and back (requirement NFR6, AC6.2).
7. Secrets are not in the pipeline; they are created on the server as files and mounted by Compose.

## Stage And Gate

| Stage | Gate |
|---|---|
| Pull request | ruff, pytest with real PostgreSQL, load script |
| Merge to main | Image build and scan; release notes |
| Transfer to registry | Manual, by digest, with the content scan the environment requires |
| Production upgrade | Manual with the documented steps; ready check green |
