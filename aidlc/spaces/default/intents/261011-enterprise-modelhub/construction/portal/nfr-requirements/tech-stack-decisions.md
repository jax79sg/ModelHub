# Technology Decisions: portal

Choices for this unit; the portal grows from the existing web app (package hubsite).

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR10.1 | Works in the current and previous versions of Chrome, Edge and Firefox. | Tested in those; Safari is not covered | NFR10, NFR questions Q2 A |
| NFR9.1 | Python 3.12, FastAPI, uvicorn, Jinja2 templates, the existing markdown-it-py and nh3 sanitiser; server-rendered pages with optional small scripts. | Same as the prototype | NFR9, NFR questions (stand-in) Q1 A |
| NFR9.2 | Authlib for the Keycloak sign-in (code exchange with proof key, state, refresh). | Chosen so we do not write security-sensitive code ourselves | NFR5, NFR questions Q1 A |
| NFR9.3 | httpx calls the Catalog and the retention service with the person's token and a request id; 5-second connect and 30-second read limits. | Shared timeouts from the common library | NFR9 |
| NFR9.4 | Sessions in memory; one copy of the portal. | A restart signs everyone out; accepted | NFR9, functional design FDQ2 A |
| NFR9.5 | Tests are pytest, written before the code, with the Catalog and Keycloak stood in; ruff (line length 100). The prototype's 24 tests are kept and adapted. | Team practice | NFR9, team.md |
| NFR8.1 | The portal connects only to the Catalog, the retention service and Keycloak. | None to the internet; no CDN, font or avatar from outside | NFR8 |
| NFR6.1 | Structured JSON logs and live and ready checks as for the other server units; the ready check reports the Catalog and Keycloak as degraded when down. | Shared conventions (contract C7) | NFR6 |
| NFR3.1 | Available in business hours; back within 4 business hours; a restart signs people out. | Restart policy; previous image kept | NFR3 |
| NFR4.1 | A failed call to a service shows a plain message and nothing partly changed on the portal side, since the portal keeps no data. | No state to repair | NFR4 |
