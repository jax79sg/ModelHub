# Technology Decisions: import-cli

Choices for this unit; the program stays the existing Python command-line tool.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR9.1 | The existing Python command-line tool (Typer), single-file program and offline packs; the new commands are login, logout and import. | Same build and release as today | NFR10 |
| NFR9.2 | httpx for talking to the import service (already installed through huggingface_hub). | No new dependency in the packs | NFR9, NFR questions Q1 A |
| NFR9.3 | The existing cryptography package verifies bundle signatures; the existing bundle code is reused. | Shared with the server-side re-check | FR1.14, ADR-005 |
| NFR9.4 | Tests are pytest, written before the code, against the Artifactory stand-in's service counterpart (a fake import service) on Linux, Windows and macOS; ruff (line length 100). | The existing CI matrix | NFR9, team.md |
| NFR8.1 | No connection except to the configured server. | A test blocks other sockets | NFR8 |
