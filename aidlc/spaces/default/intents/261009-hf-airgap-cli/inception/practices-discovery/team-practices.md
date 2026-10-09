# Team Practices

Affirmed by the interview in `practices-discovery-questions.md` on 2026-10-09. Evidence is in `evidence.md`.

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

## Deployment

This tool is a command-line program, not a live service. On merge to `main`, automated checks run on a service or machine of our choosing and produce installable files, which are handed over directly. Moving those files into the air-gapped environment is a separate manual step that follows the content scan and approval that environment requires, and it is the only gate before use there.

## Code Style

We use `ruff` for both checking and formatting, with a line length of 100, as configured in `pyproject.toml`. Python names follow the language standard: lowercase with underscores.
