# CI/CD Pipeline: platform

How the images, the Compose file and the operator guide are built, signed, carried across and put on the server.

## Steps

1. The existing GitHub Actions workflow gains an image job on merge to main: it builds the four images (portal, catalog, artifactory-service, and the proxy configuration on the official nginx image), pins the official postgres and nginx images by digest, scans every image and fails on a fixable critical finding.
2. The job produces one signed server pack: the images as archives, the Compose file with release tags and digests, the proxy configuration, the database set-up step, the operator script, the operator guide and a checksum list, signed with the project's bundle-signing key.
3. A check fails the build if any image or the single-file program contains the Artifactory stand-in, or if the Compose file uses a tag called latest or an environment variable that looks like a secret.
4. A smoke test in CI starts the whole Compose stack with the stand-ins for Artifactory and Keycloak, runs a first import through the proxy from the built program, and checks the model appears in the portal list.
5. The server pack is carried across the air gap by the same manual, scanned hand-over used for the offline packs; on the server it is verified against the trusted key before anything is loaded.
6. Deployment is manual and rehearsed (see Upgrade And Return Steps); there is no automatic deployment to production, in line with the organisation's gate for production.
7. Secrets are never in the workflow or the pack; the operator script creates them on the server.

## Stage And Gate

| Stage | Gate |
|---|---|
| Pull request | ruff, pytest of each unit, image build and scan, stand-in absence check |
| Merge to main | Server pack build and signing; whole-stack smoke test |
| Hand-over | Manual carry across with the required content scan |
| Server | Verify pack signature; load images; upgrade or return by the documented steps |
