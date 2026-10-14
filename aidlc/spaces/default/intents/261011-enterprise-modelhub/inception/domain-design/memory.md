<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-10-12T09:10:00Z — read the "import service" in IQ9 A as a real container the user intended, even though FQ2 and FQ9 had the CLI importing directly; asked DQ1 to settle it instead of picking, and the user chose the service (B), against my recommendation of A.
- 2026-10-12T09:10:00Z — treated the import service as the caller of the Catalog (acting for the person, passing their token), which keeps DQ2 A ("through a data interface") true after DQ1 B.

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-10-12T09:10:00Z — edited already-approved documents (requirements.md, raid-log.md) from inside Domain Design, because DQ1 B and DQ6 B changed what they say; every edit is tagged in the text and listed in decisions.md under "Effects On Approved Documents" so the owner can see them at this gate.
- 2026-10-12T09:10:00Z — first wrote components.md claiming the Catalog is the only way anyone reaches the database, which is false because the import service and Retention own records of their own; corrected before the gate.
- 2026-10-12T09:10:00Z — traceability.json marks FR6 (hosting) as Deferred, not OK: hosting is realised by packaging and deployment, which this stage does not decide.

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-10-12T09:10:00Z — kept ImportJob and TrustedKey in the import service and the retention setting and decisions in Retention, in their own tables of the shared PostgreSQL, rather than routing everything through the Catalog; avoids cross-component transactions at the cost of the Catalog not being the only component with database access.
- 2026-10-12T09:10:00Z — modelled a skipped import as leaving no trail row; recorded as OQ4 rather than decided.

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-10-12T09:10:00Z — OQ1 to OQ5 in components.md (Keycloak sign-in without a browser, how very large packages are sent, how trusted keys are added to the service, whether skips are recorded, single request or job).
