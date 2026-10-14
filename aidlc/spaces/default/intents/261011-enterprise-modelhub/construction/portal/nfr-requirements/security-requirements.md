# Security Requirements: portal

The portal holds the people's tokens and renders text from outside, so both sign-in and rendering are in scope.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR5.1 | Every page except sign-in, sign-out, callback, health and static files needs a session. | A test requests every route without a session | NFR5a, rule BR1.1 |
| NFR5.2 | The server holds the tokens; the browser holds only a session cookie that is Secure, HTTP-only and same-site. | A test inspects cookies and page source for tokens | NFR5, rule BR1.2 |
| NFR5.3 | The sign-in uses the standard code exchange with a proof key and a checked state value. | Tested against a Keycloak stand-in; no implicit flow | NFR5, NFR questions Q1 A |
| NFR5.4 | Forms that change something carry a session-bound token and a same-origin check. | A test posts from another origin and is refused | NFR5, rule BR1.3 |
| NFR5.5 | Administrator screens work only for the administrator role, checked again by the services. | Tests with and without the role | NFR5, rule BR1.4 |
| NFR5.6 | Model-card text is sanitised; no script runs; nothing is requested from outside the organisation. | The prototype's tests are kept and extended; a test with hostile README content | NFR5, rule BR1.10 |
| NFR5.7 | Documents and pictures from the Catalog are shown as data only, never as pages. | Content security policy, nosniff and no html or svg rendering | NFR5, rule BR1.10 |
| NFR5.8 | A made token's value is shown once, never in an address, never cached, never logged. | No-store headers; a test greps logs | NFR5b, rule BR1.12 |
| NFR5.9 | The portal serves no model file. | The download and raw routes do not exist | NFR5d, rule BR1.9 |
| NFR5.10 | Sessions end after 8 idle hours, at sign-out, or when tokens cannot be refreshed. | Tested with a short idle setting | NFR5, rule BR1.2 |
| NFR5.11 | Secrets (the sign-in client secret) come from secret files only. | None in images, files, logs or pages | NFR5b |
