# Team-Level Rules

> This team's affirmed practices and corrections. Loaded after `org.md` as
> strict-additive guidance; contradictions with broader policy are rejected.
> Populated by the practices-discovery affirmation gate. Edit at the gate,
> not directly.

## Way of Working

We use trunk-based development. Work merges into `main` through short-lived branches, and each piece of work is squash-merged into a single commit. The project is being put under version control on a code host we already use.

## Walking Skeleton

We always build a thin end-to-end slice first for each new piece of work, to prove the pieces connect before the real features go in.

## Testing Posture

- **Methodology**: tdd
- **Methodology evidence**: chosen in the interview (Q4); the existing prototype's tests were written after the code, so this is a change of habit for new work.
- **Ordering**: Write a failing test for each behaviour first, then the code that makes it pass, then tidy up.
- Every change has a test for it, and the existing tests keep passing. There is no percentage coverage floor.
- The test tool is `pytest`; tests live in `tests/`.

## Guard Policy

<!-- Affirmed by the team. Mode: strict, relaxed, or off. Strict here holds for every intent, whatever one person asks in chat; relaxed or off here applies to every intent whose policy came from its scope, unless project.md or the person sets another; changing this line changes it. A section under the retired Change Control heading, written by an earlier release, is still read. -->

## Deployment

This tool is a command-line program, not a live service. On merge to `main`, automated checks run on a service or machine of our choosing and produce installable files, which are handed over directly. Moving those files into the air-gapped environment is a separate manual step that follows the content scan and approval that environment requires, and it is the only gate before use there.

## Code Style

We use `ruff` for both checking and formatting, with a line length of 100, as configured in `pyproject.toml`. Python names follow the language standard: lowercase with underscores.
## Forbidden

<!-- Team-specific forbidden patterns -->

## Mandated

<!-- Team-specific mandates -->

## Corrections

<!-- Self-learning loop appends here. -->
