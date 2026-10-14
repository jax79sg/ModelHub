<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-10-12T15:10:00Z — FDQ3 B changed an approved Catalog rule (BR1.2/BR1.12 and its state table); edited in place and noted in the Catalog diary.
- 2026-10-12T15:10:00Z — decided that the plan 'finish' still needs every piece sent (the documents for the Catalog are inside the bundle); the CLI design must respect this.

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-10-12T15:10:00Z — getting the service token for Catalog calls (client credentials) is this unit's job, as common leaves it out; shape it in NFR/infrastructure design.
- 2026-10-12T15:10:00Z — retention default is 365 days (FR5.1); maximum 3650 and max_running_imports 2 are my defaults.

- 2026-10-12T15:45:00Z — added BR1.22 (426 for a too-old program) after import-cli design needed it.
