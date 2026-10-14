<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-10-12T07:30:00Z — read RQ13 C (add one administrator role) as overriding RQ3 A (no roles) for settings and retention only; browsing and fetching stay open to every signed-in person.
- 2026-10-12T07:30:00Z — read RQ9 C ("a person decides each time") as a choice between keeping a version (age restarts) and removing it; the two outcomes are my definition, listed as assumption A3.
- 2026-10-12T07:30:00Z — declared Artifactory the source of truth for files and the database for information and trail (FR1.5, FR1.6), because the user left the half-imported case open apart from RQ5 A.

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-10-12T07:30:00Z — the code-scan stage was skipped in the plan, so the existing tool was described from the earlier contract summary and the web app's README rather than a fresh scan; stated in the intent analysis.
- 2026-10-12T07:30:00Z — wrote one questions-file addition with a shell heredoc (Q13 and Q14) instead of the file tools; the content is correct and the file shows no damage.

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-10-12T07:30:00Z — wrote the corner cases (half-finished import, services down, two imports at once, odd names) straight into requirements with defaults rather than asking, to keep the question count at 14; the user can correct them in the document.
- 2026-10-12T07:30:00Z — accepted RQ11 A (ordinary rows for the import trail) although security is a top quality (SQ6 A); recorded as an accepted limit in NFR5 and out of scope, not argued.

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-10-12T07:30:00Z — how the CLI signs in through Keycloak on a computer with no internet (A6).
- 2026-10-12T07:30:00Z — which Keycloak setting marks an administrator.
