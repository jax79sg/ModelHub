# NFR Requirements Questions: artifactory-stand-in

Context: "NFR" means quality targets: speed, security, size, reliability and visibility. The stand-in is a test-only imitation of Artifactory (never delivered), so most targets are modest and I have written them as defaults in the answers below for you to correct. Two choices are yours: the technology the server units are written in (this answer is reused for every server unit, `catalog`, `artifactory-service`, `portal` and `common`) and where the tests that use the stand-in must run.

My defaults for this unit (not questions): it starts in under 2 seconds; answers any call except a file transfer in under 50 milliseconds on the build machine; handles a declared file of 1 TiB without holding it (virtual files, rule BR1.9); keeps memory under 500 MB for a test run; binds to 127.0.0.1 only and uses only the test's token; logs with the shared log shape; no availability target, since it only lives as long as a test.

## Q1. What should the server units be written in?

Why we ask: the web app prototype is Python with FastAPI and the CLI is Python, so reuse is high; the choice affects every server unit's tools, images and tests (requirements NFR9 test-first, team practice ruff and pytest).

- Option A, Python 3.12 with FastAPI and uvicorn (as the prototype), PostgreSQL through the psycopg 3 driver with plain SQL and numbered migration files. Pros: reuse of the prototype and the CLI's code (bundle checking, signing); one language; plain SQL suits the full-text and substring search the Catalog needs; few dependencies. Cons: hand-written SQL needs care.
- Option B, as A but with SQLAlchemy and Alembic for the database. Pros: familiar to many; migrations tool included. Cons: more dependencies; the search features still need raw SQL.
- Option C, another language (for example Go or Java) for the new services. Pros: a single binary or strong typing. Cons: loses reuse of the bundle checking code, which the import service must run again (decision ADR-005); a second language and tool chain to maintain.
- Recommendation: A.

A. Option A: Python 3.12, FastAPI, uvicorn, psycopg 3 with plain SQL and migration files
B. Option B: Python 3.12, FastAPI, SQLAlchemy and Alembic
C. Option C: another language
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. On which systems must the tests that use the stand-in run?

Why we ask: the import command must behave the same on Linux and Windows (NFR10), and its tests need the stand-in; the server units run only in Linux containers.

- Option A, the same systems as the existing CLI tests: Linux, Windows and macOS, Python 3.10 and 3.12. Pros: the CLI's import tests run everywhere it is delivered. Cons: the stand-in must also run on all of them (its code uses nothing system-specific, so little extra).
- Option B, Linux only. Pros: cheapest. Cons: Windows import behaviour (NFR10) would be untested.
- Recommendation: A.

A. Option A: Linux, Windows and macOS; Python 3.10 and 3.12
B. Option B: Linux only
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A
