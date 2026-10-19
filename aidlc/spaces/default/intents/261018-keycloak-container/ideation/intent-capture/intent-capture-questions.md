# Intent Capture Questions

## Sources

- [desc] Initial description: "Add a separate Keycloak container to the server stack and configure it for ModelHub (realm, the portal and import-service clients, the administrator role, a test user), and use the Artifactory stand-in for Artifactory testing"
- [scope] Workflow-selected scope: `feature`.

## Q1. Where does this Keycloak run?

The server stack so far expects the organisation's own Keycloak (an outside system). Where should the new container live?

A) In a separate test and development companion file next to the stack, never in the signed server pack, so the real server still uses the organisation's Keycloak
B) In the main stack file, so every install brings its own Keycloak
C) Not yet defined
X) Other (please specify)

[Answer]: A. In a separate test and development companion file, never in the signed server pack

## Q2. What is the problem this solves, and what does success look like?

A) A real Keycloak can be started with one command, already set up for ModelHub, so the sign-in path (portal login, personal tokens, service identity) can be tried and tested for real instead of against the test imitation
B) The organisation's Keycloak must be set up for ModelHub, and this gives the exact settings to copy there
C) Both A and B
D) Not yet defined
X) Other (please specify)

[Answer]: C. Both A and B

## Q3. What must the Keycloak be set up with?

The design needs: a realm; a sign-in client for the portal (authorisation code with a proof key); a service client for the import service (client credentials); an administrator role named `modelhub-admin`; and test people.

A) Exactly that: one realm, the portal client, the import-service client, the `modelhub-admin` role, one ordinary test user and one administrator test user
B) Exactly that, plus nothing else, and the names and secrets are generated for each start
C) Not yet defined
X) Other (please specify)

[Answer]: A. Exactly that set (realm, portal client, import-service client, modelhub-admin role, one ordinary and one administrator test user)

## Q4. Which Keycloak?

A) The current long-term-support release of the official Keycloak image, pinned to an exact version (so it can be carried into an air-gapped place as an image)
B) A specific version I name
C) Not yet defined
X) Other (please specify)

[Answer]: A. Current long-term-support release, pinned to an exact version

## Q5. What does this first version leave out?

A) Production hardening of Keycloak (its own database, TLS, clustering, backups), single sign-on with the organisation's directory, and anything about Artifactory itself (the stand-in is used)
B) Nothing is left out
C) Not yet defined
X) Other (please specify)

[Answer]: A. Production hardening, directory single sign-on and Artifactory itself are left out

## Assumption Confirmation

Assumptions in the stakeholder map:
- The person who requested the work decides scope and priority.
- No reporting cadence is needed.

A. Accept assumptions
B. Convert to follow-up questions

[Answer]: A. Accept assumptions

## Consolidated Summary Confirmation

Summary of your answers: a real Keycloak runs from a separate test and development companion file, never in the signed server pack; success is both a one-command real Keycloak for testing and the exact settings written down for the organisation's Keycloak; it holds one realm, the portal client, the import-service client, the modelhub-admin role, one ordinary and one administrator test user; it uses a pinned long-term-support release of the official image; production hardening, directory single sign-on and Artifactory itself are left out.

Does this all look correct?

[Answer]: Looks correct
