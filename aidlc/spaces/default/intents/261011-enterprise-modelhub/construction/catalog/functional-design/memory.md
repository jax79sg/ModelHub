<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-10-12T14:10:00Z — FDQ6 B (delete documents on removal) was the human's choice against the recommendation: space is freed but a removed version's card can no longer be shown, and the README text is cleared from search.

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-10-12T14:10:00Z — decided that a skipped or repaired import still adds one trail row (BR1.13); an earlier open question, now an assumption the human can reverse at the gate.
- 2026-10-12T14:40:00Z — changed after artifactory-service FDQ3 B: a new record for a removed version reinstates it (BR1.2, state table, edge case updated).
- 2026-10-12T14:10:00Z — 16 MiB per document and 20 active tokens per person are my defaults, not answers.
