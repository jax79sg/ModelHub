<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-10-12T05:10:00Z — read Q10 ("If it's already there and not a different version, the action should stop right.") as a rule about repeated imports of the same commit, not about migrating the old folder; asked Q12 and Q13 to settle the migration and the stop-versus-skip behaviour (answers: import the old folder's models; skip a repeated model and carry on).
- 2026-10-12T05:10:00Z — treated Q9 A (use `jf hf upload`) as the user's choice for the upload step only; the download side keeps `huggingface_hub` 2.2+. The resulting two-client situation is recorded as risk R1 rather than silently resolved.

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-10-12T05:10:00Z — the stage prose asks about AWS services and accounts; replaced by Q1 and Q8 (internal registry, monitoring, Linux server) because the architecture is on-premises in Docker and AWS is not mentioned. The AWS and compliance support agents were not used (collaborators off).
- 2026-10-12T05:10:00Z — research source was JFrog's public documentation read in the built-in browser, not a test against Artifactory (none is available); everything resting on it is labelled as an assumption.

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-10-12T05:10:00Z — chose to describe the Artifactory emulation's feasibility from the installed `huggingface_hub` 2.2.0 source (endpoints it builds) rather than 1.19.0 (the newest Artifactory supports), because 1.19.0 was not installed; the difference is stated in the assessment.

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-10-12T05:10:00Z — how long must old model versions be kept (Q3 option C was chosen without a length)?
- 2026-10-12T05:10:00Z — how big will the store be (Q5 "not yet defined")?
- 2026-10-12T05:10:00Z — can the import computer carry the JFrog CLI, Python 3 and `huggingface_hub` 1.19.0 or older next to the single-file `modelhub` program, or should the upload be isolated?
