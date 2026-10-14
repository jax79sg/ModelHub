# CI/CD Pipeline: import-cli

How the program with the import commands is built, tested and released: the existing pipeline, with new tests.

## Steps

1. A pull request runs ruff and pytest (written first) for the import commands on Linux, Windows and macOS with Python 3.10 and 3.12, against a fake import service built on the stand-in's server pieces.
2. Tests stop the process at each state of the transfer, tamper with a piece, drop the network with the failure switches, and search every output for the token.
3. The existing smoke test (the round trip of a bundle) is extended with login and import against the fake service.
4. On release the existing workflow builds the single-file programs and offline packs for the three systems as today; the import commands add no new files.
5. Release notes state the new commands, that the server must be 'ready' first, and the minimum server version the program supports.
6. There is no deployment or rollback beyond handing out the previous release's files; there are no secrets in the pipeline.

## Stage And Gate

| Stage | Gate |
|---|---|
| Pull request | ruff, pytest on Linux, Windows, macOS; fake service tests; token-leak search |
| Release | Existing build of programs and packs; smoke test with login and import |
