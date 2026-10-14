# Risk And Sequencing Rationale

A **Bolt** is one build pass over a piece of the work, here one unit taken through its four design runs. This file explains why the Bolts in `bolt-plan.md` are in that order. A **walking skeleton** is the smallest slice that runs from one end of the system to the other; a **mob** is a group working together.

## The Rule That Fixes Most Of The Order

The dependency list in `inception/units-generation/unit-of-work-dependency.md` is a hard limit: a unit is designed only after the units it needs. Within that limit three orders are possible. Only the relative order of B1 and B2 and the position of B6 are free; everything else is forced:

- B1 and B2 depend on nothing, so they come first (either order).
- B3 needs B1; B4 needs B1, B2 and B3; B5 needs B1, B3 and B4; B7 needs B3, B4 and B5; B6 needs only B4, so it could go before B5.

## Why Risk-First (Option A, DPQ1)

Risk, not value, was chosen as the tie-breaker. No scoring model (WSJF, which ranks work by value and urgency divided by size) was used: the order is almost entirely forced by dependencies, and a score would not change it, so the extra numbers would only look precise.

The largest unknowns sit in B4 `artifactory-service` (the unit that talks to Artifactory), and its design depends on three things settled earlier in the order:

1. **B1 common** supplies the token check that B4 uses.
2. **B2 stand-in** records every Artifactory behaviour we assume and gives B4 something to design its tests against.
3. **B3 catalog** fixes what B4 records and in what single transaction.

So B4 comes as soon as it can, with its three prerequisites done. Doing it late (value-first) would leave the riskiest design for last, when a surprise would force changes in `catalog` and `portal` already approved. Platform-first (DPQ1 C) was rejected because B7 depends on three units and would be designed against guesses.

B5 `portal` follows B4 rather than preceding it because the retention and key screens depend on B4's interface (contract C4). B6 `import-cli` is placed after B5 only to put the part people see before the part that sends data; it could go first without harm. If you prefer the CLI sooner, swap B5 and B6.

## Ranking Of The Risks

| Risk | Where it bites | How the order handles it |
|------|----------------|--------------------------|
| How Artifactory's Machine Learning layout lists and deletes files is not documented on the pages read | B4 | The gateway discovers paths by listing instead of building them; the stand-in (B2) records the assumption; the checklist is confirmed on the real Artifactory when possible (see `external-dependency-map.md`) |
| A very large package (over 100 GB) interrupted mid-transfer | B4, B6 | B4 is designed early so the resume rules are settled before the CLI is designed against them |
| Personal tokens leaking or living too long | B3, B5, B6 | The Catalog (B3) stores hashes only; defaults are an open question for the owner |
| Retention deleting the wrong thing | B4, B5 | Delete-then-mark order and administrator-only screens are designed in B4 before B5 shows them |
| Hosting details (registry, logging) unknown | B7 | Last, so every other unit's needs are known; assumptions recorded |

## Why The Skeleton Is Handled The Way It Is

The team's practice is to build a thin end-to-end slice first. This plan has no code, and the first unit by dependency, `common`, is a library, not a slice. Rather than reorder to something false, the plan keeps the dependency order and spreads the skeleton: B3 to B6 each design their part of one named trace (a tiny model going from the CLI to the portal), and B7 closes it with a written end-to-end walk-through (see `bolt-plan.md`). This departs from the practice in letter, not in intent, and is flagged for you at the gate. The alternative, designing a thin path through all units first, would mean designing B4's parts before B1 to B3 are settled, which reverses the dependency order and is rejected.

## Order Of Design Runs (DPQ3)

Unit by unit means each unit's four runs finish before the next unit starts. The trade-off accepted: a late discovery in a unit's infrastructure run can reopen an earlier unit. The alternative, run by run, was rejected because it leaves all seven units open for a long time.

## Heuristic Used

Dependency-driven sequencing with risk-first tie-breaking, in the spirit of Cohn's "do the riskiest thing early" rule; no numerical model.
