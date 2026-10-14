# Delivery Planning Questions

Context: this stage chooses the order in which the seven units of work are taken through the Construction design stages. A **Bolt** is one pass over a piece of the work, ending in something you can check; here each Bolt is one or more units taken through their four design runs (functional design, quality requirements, quality design, infrastructure design). The dependency order is already fixed by Units Generation: `common` and `artifactory-stand-in` depend on nothing; `catalog` needs `common`; `artifactory-service` needs `common`, `catalog` and the stand-in; `portal` needs `common`, `catalog` and `artifactory-service`; `import-cli` needs `artifactory-service`; `platform` needs `catalog`, `artifactory-service` and `portal`. Any order below must respect that.

This whole plan stops at the architecture, with no code. So a Bolt here ends in approved design documents, not a running program. Your team practice says to build a thin end-to-end slice first (a **walking skeleton**: the smallest piece that runs from one end of the system to the other); in a design-only plan that means the first Bolt designs the thinnest path through every part.

Questions about contract ownership, sign-in and the unit sizes are already settled in earlier stages. The rest of the Bolt details (who does the work: the developer agent in this session; what each Bolt's checks are) I will fill with defaults and write down for you to correct.

## Q1. What should be designed first?

Why we ask: this decides the order of the seven units within the limits of the dependencies.

- Option A, dependency-first with the riskiest part early: `common` and `artifactory-stand-in` first (nothing waits on them), then `catalog`, then `artifactory-service` (the largest and riskiest: it holds the Artifactory unknowns), then `portal`, `import-cli`, `platform`. Pros: the hardest design is settled while the choices are still open; later units design against settled contracts. Cons: the first Bolts show nothing a person can click.
- Option B, value-first: `common`, `catalog`, `portal` first so the browsing side is designed early, then `artifactory-service`. Pros: the part people see comes first. Cons: the biggest unknown (how Artifactory stores files) is left late, and the portal may need redesign if it changes the Catalog.
- Option C, platform-first: `platform` early so the server layout is settled first. Cons: it depends on three units, so it cannot go first without designing against guesses.
- Recommendation: A.

A. Option A: dependency-first, riskiest part early
B. Option B: value-first
C. Option C: platform-first
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. How big should one Bolt be?

Why we ask: it sets the number of Bolts and so the number of approval points.

- Option A, one unit per Bolt (7 Bolts). Pros: each Bolt has one clear answer to "is it done"; easy to review. Cons: the two roots, `common` (small) and `artifactory-stand-in`, are each a thin Bolt.
- Option B, group the small neighbours: Bolt 1 `common` plus `artifactory-stand-in`; then one unit each for the rest (6 Bolts). Pros: fewer approval points for the two units that depend on nothing. Cons: the Bolt mixes unrelated things.
- Option C, thin slices across units, such as "list a model" or "import a model" that each touch several units (about 4 Bolts). Pros: matches how people see the system. Cons: each Bolt reopens several units, and the engine builds unit by unit, so it works against the order Construction actually follows.
- Recommendation: A.

A. Option A: one unit per Bolt (7 Bolts)
B. Option B: group `common` and `artifactory-stand-in` (6 Bolts)
C. Option C: thin slices across units
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. In what order should the design runs go?

Why we ask: this decides whether each unit finishes all four design runs before the next unit starts, or all units do the first run together, then the second, and so on.

- Option A, unit by unit (the default): each unit finishes its four design runs, then its approval, then the next unit. Pros: a later unit designs against an approved, complete earlier one; a wrong turn is caught within one unit. Cons: a late discovery in one unit's infrastructure run can reopen an earlier unit's design.
- Option B, run by run: every unit's functional design first, then every unit's quality requirements, and so on. Pros: cross-unit questions surface together. Cons: a very long stretch before anything is complete; seven units at a time is a lot to hold in mind.
- Recommendation: A.

A. Option A: unit by unit
B. Option B: run by run
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. Can Bolts overlap?

Why we ask: in this session the design is done one piece at a time. Parallel designing would need several people or agents, and you asked earlier that no sub-agents be used.

- Option A, one after another (serial). Pros: simple, no merge conflicts between design documents; matches your earlier instruction. Cons: slower than parallel work.
- Option B, allow independent units to go in parallel (`common` and `artifactory-stand-in`, and later `portal` with `import-cli`). Pros: faster. Cons: needs a second worker; conflicts with the no-sub-agents instruction.
- Recommendation: A.

A. Option A: serial
B. Option B: parallel where independent
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. What outside things could hold the build up, and what worries you most?

Why we ask: the plan should tackle these early or note what to do if they slip. From the earlier stages, the ones I know of are:

1. How Artifactory's Machine Learning layout lists and deletes files (not documented on the JFrog pages read); only confirmable on the real Artifactory. Blocks the final gateway design in `artifactory-service`.
2. Keycloak: the two client ids and the `modelhub-admin` role must be accepted by the people who run Keycloak. Blocks `common` (token check) and `portal`.
3. The container registry and central logging: the details of how our images and logs reach them. Blocks `platform`.
4. The owner's answers on the personal-token defaults (90 days, import only). Blocks `catalog` and `portal`.

- Option A, record these in the plan with an owner, an expected wait and a fallback, and carry on designing with the stated assumption; confirm each when its owner answers. Pros: nothing waits on a person. Cons: a wrong assumption means redoing part of one unit.
- Option B, stop at each blocker until it is answered. Pros: no rework. Cons: the whole plan waits on others.
- Recommendation: A. Say in the answer if there is a dependency I have missed, or a worry you want tackled first.

A. Option A: record, assume and carry on
B. Option B: stop at each blocker
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q6. How do you want to staff Construction, and how do you want to verify it?

Why we ask: two settings the next phase needs. Staffing: this session does all the work (your earlier choice), or each of several teams owns a unit. Verification: Construction normally runs one project check at the end of each unit. This plan produces no code, so there is nothing for such a check to run yet.

- Option A, this session does everything, and no verification command now (decide at the first checkpoint, when there may be a check worth running, such as the document checks). Pros: matches the work. Cons: none for a design-only plan.
- Option B, this session does everything, and use the existing test command (`pytest`) as the check. Pros: a command is recorded. Cons: it tests the existing CLI, not the new design, so a pass would say nothing about this work.
- Option C, several teams each own a unit. Pros: if more people join. Cons: nobody else has been named.
- Recommendation: A.

A. Option A: this session does everything; no verification command now
B. Option B: this session does everything; use `pytest`
C. Option C: several teams each own a unit
D. Not yet defined
X. Other (please specify)

[Answer]: A
