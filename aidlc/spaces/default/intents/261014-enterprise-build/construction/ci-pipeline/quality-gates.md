# Quality Gates

## Summary

The person chose to require the checks and a pull request before anything merges to `main`. This is the list to set in GitHub (Settings, Branches, rule for `main`: require a pull request, require status checks to pass). It could not be applied by the tools: the access token they use got 403 on branch protection.

## Sources

- `ci-pipeline-questions.md`, answer 3
- `.github/workflows/ci.yml` (job names as GitHub shows them)
- `construction/build-and-test/test-results.md`

## Required before merge (33 checks)

`lint`; `test` on ubuntu, macos and windows with 3.10 and 3.12 (6); `build-linux`, `build-macos`, `build-windows`, `run-linux-on-ubuntu-20-04`; `offline-pack` on ubuntu and windows with 3.10 and 3.12 (4); `web` on ubuntu, macos and windows with 3.10 and 3.12 (up to 6, as GitHub lists them); `server (3.10)`, `server (3.12)`; `stand-in` on macos and windows with 3.10 and 3.12 (4); `browser (chrome)`; `images`; `CodeQL` and `Analyze (actions)`, `Analyze (javascript-typescript)`, `Analyze (python)`.

## Not required

`GitGuardian Security Checks` stays visible but does not block: it can flag key-shaped test fixtures. `server-pack` runs only on `main` and is skipped on pull requests, so it cannot be required there.

## Gates and what each one stops

| Gate | Stops |
|---|---|
| Lint and format | Style drift |
| Tests on three systems, two Python versions | A change that breaks the program on a supported system |
| Server units on PostgreSQL | A change that breaks the Catalog, import service, portal or their whole-stack path |
| Images job | A change that breaks the images, adds a secret, a stand-in or the JFrog CLI where it must not be, a critical fixable vulnerability, the smoke test or the rehearsal |
| Chrome job | A change that breaks the portal in the browser |
| CodeQL | New static security findings |

## Rules for the gates

- A gate is never weakened to make a change pass; a failing gate is fixed or the change waits.
- Strict "branch up to date" is off, so a squash-merge queue is not needed for this team size.
- Administrators are not exempt from the checks once the person turns on "include administrators"; today that is left to the person.

## Assumptions & Open Questions

- Whether to also require one human review is not decided; the person chose checks and a pull request only.
