# CI Pipeline Questions

CI already exists in this repository (`.github/workflows/ci.yml` and `release.yml`) and was extended through Build and Test. These questions confirm what is in use and settle what is not yet enforced.

## Question 1: CI tool

GitHub Actions is in use for every job (lint, tests on three systems, the three program builds, the server units, the Chrome test, the images with scan and smoke test, the signed server pack on main).

A) Keep GitHub Actions
B) Other (please specify)

[Answer]: A (found in the repository; confirmed by the person's use of it throughout)

## Question 2: Branch strategy

Trunk-based: short branches into `main`, each squash-merged (team rule in `team.md`).

A) Keep trunk-based with squash merges
B) Other (please specify)

[Answer]: A (team rule `team.md`)

## Question 3: Quality gates required before merge

Today `main` has no branch protection, so a failing check does not stop a merge. Proposed required checks: lint, test (all six combinations), server (3.10 and 3.12), stand-in (four combinations), web, offline-pack, browser (chrome), images, build-linux, build-windows, build-macos, CodeQL. GitGuardian is not required (it can fail on test fixtures); it stays visible.

A) Require these checks and a pull request for `main` (the person sets it in GitHub, or asks me to)
B) Do not enforce; keep the checks advisory
C) Other (please specify)

[Answer]: A (the person chose "Require checks and a PR"). Not yet applied: the access token the tools use cannot change branch protection (GitHub answered 403), so the person applies it in GitHub (Settings, Branches, rule for main) with the checks listed in quality-gates.md.

## Question 4: Artifact repository

No registry is used: the CLI programs are released by `release.yml`, and the server pack (signed images, compose file, guide, monitoring files) is built by the `server-pack` job on `main` and carried by hand across the air gap (`team.md`, Deployment).

A) Keep it that way (pack as a CI artifact, no registry)
B) Other (please specify)

[Answer]: A (team rule `team.md`)
