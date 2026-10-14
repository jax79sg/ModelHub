# CI/CD Pipeline: artifactory-stand-in

How the stand-in is built, tested and kept out of what is delivered, using the existing GitHub Actions pipeline.

## Steps

1. A pull request runs ruff (check and format, line length 100) and pytest for the stand-in on Linux, Windows and macOS with Python 3.10 and 3.12.
2. Tests are written first; the register test lists every answer the stand-in can give and fails if one has no assumption entry.
3. The stand-in lives in the test tree (not the packaged program); the release workflow builds the images and the program from the package folders only.
4. A release check searches the built images and the single-file program for the stand-in's files and fails if found.
5. The assumption checklist is published as a file in the release notes of the build for whoever has access to a real Artifactory.
6. There is no deployment, rollback or secret in this pipeline.
