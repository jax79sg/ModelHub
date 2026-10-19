# Domain Design Questions

## Q1. How is the work divided into building blocks?

A) Four blocks: the realm definition (the realm file and the check of it), the Keycloak container definition (compose file, pinned image), the test stack wiring (the second compose file and its settings), and the sign-in verification (the test that runs the real sign-in path)
B) Two blocks: everything that defines Keycloak (realm, container, wiring) and the verification
C) Not yet defined
X. Other (please specify)

[Answer]: A. Four blocks

## Consolidated Summary Confirmation

- The work is divided into four building blocks: the realm definition (realm file and its check), the Keycloak container definition (compose file, pinned image), the test stack wiring (second compose file and settings), and the sign-in verification (the real sign-in test).
- The Keycloak files are test-only and never part of the signed server pack.

Does this all look correct before I generate the component catalogue?

[Answer]: Looks correct
