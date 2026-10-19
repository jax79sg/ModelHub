# Units Generation Questions

## Q1. How is the work grouped into units?

The four building blocks are small, share one realm file and are tested together against one real Keycloak.

A) One unit `keycloak` (kind packaging) holding all four blocks, built tests first
B) Two units: the realm and container files, then the sign-in verification
C) Not yet defined
X. Other (please specify)

[Answer]: A. One unit keycloak (packaging)

## Consolidated Summary Confirmation

- One unit, `keycloak` (kind packaging, size M), holds all four building blocks and is built tests first.
- There is no dependency graph and nothing to sequence.

Does this all look correct before I generate the unit artifacts?

[Answer]: Looks correct
