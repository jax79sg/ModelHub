# Intent Statement

## Problem Statement

The ModelHub server needs people to sign in and a service to identify itself through Keycloak, but the stack has only ever been tried against a test imitation of Keycloak, and the organisation's own Keycloak has to be set up for ModelHub by hand. [desc]

## Target Customer

The team that builds, tests and installs ModelHub: they need a real Keycloak to try the sign-in path against, and the exact settings to give whoever runs the organisation's Keycloak. [Q2]

## Success Metrics

- One command starts a Keycloak that is already set up for ModelHub, and the sign-in path (portal login, personal tokens, service identity) works against it. [Q2]
- The same settings are written down so they can be applied to the organisation's Keycloak. [Q2]
- The Keycloak holds one realm, the portal client, the import-service client, the `modelhub-admin` role, one ordinary and one administrator test user. [Q3]

## Initiative Trigger

The request to add a separate Keycloak container to the server stack and configure it for ModelHub. [desc]

## Initial Scope Signal

- Workflow-selected scope: `feature`. [scope]
- Product boundary confirmed by the person: it runs from a separate test and development companion file, never in the signed server pack. [Q1] It uses a pinned long-term-support release of the official image. [Q4] Left out: Keycloak production hardening, directory single sign-on, and Artifactory itself (the stand-in is used). [Q5] [desc]

## Assumptions & Open Questions

None.
