# Unit Test Instructions: enterprise ModelHub (overall)

How the tests are run. Commands are run from the repository root with the project's virtual environment (`.venv`, Python 3.12).

## Prerequisites

- Python 3.10 or later (the project environment uses 3.12) with the project's development dependencies installed.
- Docker (OrbStack on this machine) for the tests that need PostgreSQL; those tests skip with a clear message when Docker is missing. No network is needed otherwise.

## Commands

| Scope | Command | Notes |
|-------|---------|-------|
| Existing CLI and import additions | `.venv/bin/python -m pytest tests -q` | 369 tests today; network tests are skipped by default |
| Existing portal | `.venv/bin/python -m pytest web/tests -q` | 24 tests today |
| One server unit | `.venv/bin/python -m pytest server/<unit>/tests -q` | `<unit>` is `common`, `catalog`, `artifactory_service` or `stand_in` |
| Lint and format check | `.venv/bin/ruff check . && .venv/bin/ruff format --check .` | line length 100 |

The exact per-unit command and any new fixtures are recorded here when PR 0 creates them, and each unit's own instructions repeat the one that applies.

## Test First

For every behaviour, write the failing test first and record the failing command output, then write the minimum code that makes it pass, then refactor with the tests green (the team's test-driven order).

## Environment Variables

None are needed. Tests generate their own test tokens and secrets; no real secret is used or stored.
