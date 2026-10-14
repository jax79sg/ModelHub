# CI/CD Pipeline: portal

How the portal image is built, tested and upgraded.

## Steps

1. A pull request runs ruff, pytest (written first) with the Catalog and Keycloak stood in, the prototype's tests adapted, and a hostile-README test; plus a check that the download and raw routes do not exist.
2. A browser check opens the main pages in the current Chrome, Edge and Firefox against the stood-in services (screenshots kept as build output).
3. On merge to main the release workflow builds the image from python:3.12-slim with the shared library from the same commit, tags it with the release version, scans it and fails on a fixable critical finding.
4. The image is carried to the internal registry by digest with the others (manual step with the content scan the environment requires).
5. Upgrade on the server: stop the stack, change tags, start; return: previous tags. A restart signs people out, which is accepted.
6. Secrets (sign-in client secret) are files created on the server; none is in the pipeline.

## Stage And Gate

| Stage | Gate |
|---|---|
| Pull request | ruff, pytest with stood-in services, no-file-route check, browser check |
| Merge to main | Image build and scan |
| Transfer to registry | Manual, by digest, with the required content scan |
| Production upgrade | Manual; ready green; a test sign-in |
