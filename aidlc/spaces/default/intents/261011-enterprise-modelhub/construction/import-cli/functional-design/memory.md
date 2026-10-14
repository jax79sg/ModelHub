<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-10-12T15:40:00Z — FR8 (old folder) is designed as Deferred, not built (FDQ5 C); the requirement says 'designed now, built after the first version', so the design is a reserved option only. The earlier scope said the same. Human may reverse at the gate.

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-10-12T15:40:00Z — BR1.14 relies on the service answering 426 for a too-old program (contract C1 versioning); artifactory-service has no rule for it yet, so it must be added at its NFR/infrastructure design or here as a knock-on.
- 2026-10-12T15:40:00Z — whether the server's address uses a certificate the import computers trust is not known; tied to the organisation's setup.
