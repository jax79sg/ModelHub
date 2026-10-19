# Requirements Analysis Questions

The existing code fixes what Keycloak must give it: tokens whose audience is `modelhub`; the roles in `realm_access.roles` with an administrator role named `modelhub-admin`; a portal client whose id is `modelhub` (confidential, authorisation code with a proof key, `openid` scope); a service client `modelhub-artifactory-service` (client credentials); each token carrying `sub` and `preferred_username`.

## Q1. How is the Keycloak set up and started?

A) A realm file (JSON) imported when the container starts, plus a compose file that starts Keycloak with it, so nothing is clicked by hand
B) A script that configures a running Keycloak through its admin interface
C) Not yet defined
X. Other (please specify)

[Answer]: A. A realm file imported at start, with a compose file

## Q2. What are the secrets and passwords of the test setup?

A) Fixed, clearly marked test values in the realm file (this setup is never for a real server)
B) Generated at each start and printed once
C) Not yet defined
X. Other (please specify)

[Answer]: A. Fixed, clearly marked test values

## Q3. How is it tested?

A) A test checks the realm file (clients, audience, role, users), and a test starts the real Keycloak and runs the sign-in path against it: the portal login in Chrome, a personal token, and the import service's own token; this also runs in CI
B) Only the realm file is checked by tests; the real Keycloak is tried by hand
C) Not yet defined
X. Other (please specify)

[Answer]: A. Realm file checked, and the real Keycloak started in a test and in CI

## Q4. How do people use it with the rest of the stack?

A) The same compose file adds Keycloak beside the existing stack (and the Artifactory stand-in), with a short guide: start it, sign in as the test users, and the settings to copy into the organisation's Keycloak
B) Keycloak alone, without wiring the stack to it
C) Not yet defined
X. Other (please specify)

[Answer]: A. Beside the stack, with a short guide

## Consolidated Summary Confirmation

- Keycloak is set up by a realm file imported when the container starts, with a compose file that starts it.
- The test setup uses fixed, clearly marked test secrets and passwords.
- Tests check the realm file and start the real Keycloak to run the sign-in path (portal login in Chrome, a personal token, the import service's own token), also in CI.
- The compose file adds Keycloak beside the existing stack and the Artifactory stand-in, with a short guide including the settings to copy into the organisation's Keycloak.

Does this all look correct before I generate the requirements artifact?

[Answer]: Looks correct
