# CI/CD Pipeline: artifactory-service

How the image is built (with the JFrog CLI), tested against the stand-in, scanned and upgraded.

## Steps

1. A pull request runs ruff, pytest against the Artifactory stand-in and a real PostgreSQL; the restart tests use the stand-in's failure switches to stop at every state of an import.
2. A memory test streams a declared 200 GB piece set through the pipeline with the stand-in and checks peak memory stays under 8 GB.
3. On merge to main the release workflow builds the image from python:3.12-slim, adds the pinned JFrog CLI binary and the pinned huggingface_hub, installs the shared library from the same commit, tags with the release version and scans it; a fixable critical finding fails the release.
4. A check confirms the stand-in is not in the image.
5. The image is carried to the internal registry by digest with the other images (manual step with the content scan the environment requires).
6. Upgrade on the server: stop the stack, change tags, start; database steps run under a lock; interrupted imports are failed and can be rerun. Return: previous tags.
7. The 100 GB timing target is measured on the first real Artifactory and recorded; the checklist from the stand-in is run at the same time.
8. Secrets (Artifactory token, Keycloak client secret, database password) are created on the server as files; none is in the pipeline.

## Stage And Gate

| Stage | Gate |
|---|---|
| Pull request | ruff, pytest with stand-in and PostgreSQL, memory test |
| Merge to main | Image build, pin check, scan, stand-in absence check |
| Transfer to registry | Manual, by digest, with the required content scan |
| Production upgrade | Manual; ready green; first import after upgrade watched |
