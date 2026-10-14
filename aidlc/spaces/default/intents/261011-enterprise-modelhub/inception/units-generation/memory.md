<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-10-12T10:20:00Z — read the unit-count cost (four design runs per unit) as the main driver of the grouping question and stated it up front in the questions file, since the user had not seen that Construction repeats four design stages per unit.
- 2026-10-12T10:20:00Z — placed the user's two choices (six units at UQ1 A, plus a shared library at UQ2 A) together as seven units, rather than treating UQ2 A as already inside UQ1 A; the library is U1.

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-10-12T10:20:00Z — the stage prose asks about dependency ordering and parallelism; not asked, because the graph shows only true dependencies and the parallel sets fall out of it, while the choice of order belongs to Delivery Planning.
- 2026-10-12T10:20:00Z — wrote the per-unit row counts in the story map from memory first and had them wrong (13, 22, 11, 9 instead of 11, 20, 8, 8); recomputed from the table with a script and corrected.
- 2026-10-12T10:20:00Z — the walking-skeleton ceremony is off for this scope, so no unit was shaped as a first integrated slice; stated in the dependency document.

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-10-12T10:20:00Z — kept U3 (the stand-in) as a unit with a build-and-test edge from U4, although nothing delivered depends on it; the component catalogue still shows no dependency on it, and the difference is explained in the dependency document.
- 2026-10-12T10:20:00Z — the IDs U1 to U7 look like an order; added a note that they are labels only so Delivery Planning keeps the freedom to sequence.

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-10-12T10:20:00Z — 28 design runs in Construction is a lot of approvals for a one-person project; Delivery Planning and the user may want to batch units that are alike.
