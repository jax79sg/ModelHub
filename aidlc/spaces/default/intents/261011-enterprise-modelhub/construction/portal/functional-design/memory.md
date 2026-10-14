<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-10-12T16:20:00Z — a UI unit owes no rules or entities file; I wrote rules.md because the portal has real access and failure rules and the sensor ties requirements to rule IDs.
- 2026-10-12T16:20:00Z — the prototype's download, raw and JSON routes are removed (the portal serves no model file; other programs use the Catalog).

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-10-12T16:20:00Z — FR3.8 ('signed-in people keep working until their session ends') holds only while the Keycloak access token is valid; ask the Keycloak administrators about a longer access-token lifetime.
- 2026-10-12T16:20:00Z — the fetch snippets follow JFrog's documentation and are on the checklist for a real Artifactory.
