<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
- 2026-10-17T11:12:59Z — The measurable targets were taken from the per-unit `nfr-requirements` tables of the design intent 261011, because this build intent skipped the NFR stages and its `requirements.md` points to them ("NFR1 to NFR10 and the per-unit targets"); 186 unit rows plus two system rows.

## Deviations
- 2026-10-17T11:12:59Z — Verdicts were assigned from existing tests and CI results; no new measurements were run in this stage, so every scale, timing and real-system target is Unverified rather than guessed.

- 2026-10-17T11:35:00Z — Loop-back 1: the person did not approve a not-deployment-ready result and chose to fix the 4 Not Met targets first; Code Generation is reopened for artifactory-service, import-cli and platform.

- 2026-10-17T12:10:00Z — Loop-back 2: the person chose Retry with fix for the 61 Unverified targets; the repository-checkable ones (about 35) get checks; the rest stay Unverified.

- 2026-10-18T02:20:00Z — Loop-back 3: the person chose Retry with fix for the one Unverified target with a code fix (platform NFR7.2, free space checked at start); the other 13 stay Unverified.

- 2026-10-18T03:30:00Z — The person reviewed the 13 Unverified targets and dropped 5 (catalog NFR4.1, import-cli NFR7.3, artifactory-service NFR7.1 and NFR7.2, import-cli NFR7.2). The word "speed related" was read as the three speed targets; the others (for example the planning figures) were not dropped. 8 targets stay Unverified.

- 2026-10-18T04:00:00Z — Loop-back 4: the person narrowed portal NFR10.1 to Chrome ("Nfr 10.1, just chrome."); the answer was read as authorising a fourth loop-back limited to a Chrome test of the portal. The other 7 Unverified targets were not addressed by that answer.

- 2026-10-18T05:30:00Z — Loop-back 5: the person chose to close what can be closed of the remaining 7; work lands in the platform unit (monitoring files, preflight, internal-only smoke test).

## Tradeoffs
- 2026-10-17T11:12:59Z — Offered the person a loop-back to close the 4 Not Met targets; they accepted the failure instead, so those and the 60 Unverified targets stay open and the stage is presented as not deployment-ready.

## Open questions
- 2026-10-17T11:12:59Z — Who owns the Unverified targets (100 GB import time, 20 users at once, page weight, browser support, stand-in load figures): a later performance-validation stage would have to be added to the plan.
- 2026-10-17T11:12:59Z — Whether the import service image should carry the JFrog CLI (design NFR10.1) or keep uploading through huggingface_hub only.
