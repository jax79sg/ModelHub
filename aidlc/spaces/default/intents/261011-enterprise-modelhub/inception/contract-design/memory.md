<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-10-12T11:40:00Z — read CQ4 C ("a personal token made in the portal") and CQ7 B ("the system issues its own tokens") together as: a token issued and checked by the Catalog, working for importing only; the safeguards (import-only scope, 90-day lifetime, shown once, hash only) are my defaults, listed as assumption A11 and an open question for the owner.
- 2026-10-12T11:40:00Z — treated the Catalog as the home of the token because it is already the one component that checks callers and writes the trail, and kept Keycloak for browser sign-in and for the administrator role only.

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-10-12T11:40:00Z — the stage asks about the public or external API surface; the answer is that there is none beyond Artifactory's own repository address, stated at the top of the contract summary instead of a question.
- 2026-10-12T11:40:00Z — the contract summary carries one OpenAPI block per HTTP contract but abbreviates response bodies as text descriptions; the full schemas are for Functional Design, and the abbreviation is stated.
- 2026-10-12T11:40:00Z — edited approved earlier documents again (requirements.md, components.md, decisions.md, the unit documents and two traceability files) after CQ4 C and CQ7 B; each edit is tagged and listed in the contract summary's "Effects On Approved Documents".
- 2026-10-12T11:40:00Z — wrote one sloppy line in the Artifactory contract ("CQ6 is not asked"), caught when re-reading it before the gate and corrected.

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-10-12T11:40:00Z — chose not to specify where Artifactory's Machine Learning layout stores files, because the pages read do not say; the contract says the gateway must discover paths by listing and records this as an open question instead of guessing a layout.
- 2026-10-12T11:40:00Z — put all server-side health, logging and secrets conventions in one contract (C7) owned by the shared library, so the platform unit and all services read one definition.

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-10-12T11:40:00Z — the seven open questions in the contract summary's table, chiefly how Artifactory lists and deletes files in the Machine Learning layout (C5) and the personal-token defaults (C3).
