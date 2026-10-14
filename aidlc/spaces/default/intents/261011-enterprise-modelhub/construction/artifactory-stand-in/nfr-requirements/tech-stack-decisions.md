# Technology Decisions: artifactory-stand-in

Choices for this unit; the server stack answer (FDQ in the NFR questions, Q1 A) is shared by all server units.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR10.1 | Python 3.12 in the images; tests run on Python 3.10 and 3.12. | Linux, Windows and macOS | NFR10, NFR-questions Q2 A |
| NFR9.5 | FastAPI with uvicorn, the same as the prototype web app, started inside the test run on a free local port. | No container needed for tests | NFR9, FDQ6 A (functional design) |
| NFR9.6 | Tests use pytest, written before the code; ruff for checks and format (line length 100). | Team practice | NFR9, team.md |
| NFR8.1 | The stand-in makes no connection outside the local machine. | A test blocks other sockets and still passes | NFR8 |
| NFR9.7 | No extra dependencies beyond FastAPI, uvicorn and the standard library. | Listed in the unit's project file | NFR9 |
