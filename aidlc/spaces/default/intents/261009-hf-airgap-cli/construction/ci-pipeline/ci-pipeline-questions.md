# CI Pipeline Questions

The CI pipeline is the automatic checks that run on every merge to `main`: tests on Linux and Windows, then building the single program file for each. Your code is on GitHub, and your team practices say the checks run on a service of your choosing and produce installable files that are handed over directly.

## Q1. Which service runs the checks?

Why we ask: it decides the file format of the pipeline and where the built program files appear.

A. GitHub Actions (built into GitHub; free minutes for public repositories, limited for private ones; has both Linux and Windows machines)
B. Your own machines (a Jenkins or similar server) that you already run
C. Another hosted service (GitLab CI, CircleCI, etc.)
X. Other (please specify)

[Answer]: A

## Q2. Which systems must the tests run on?

Why we ask: requirement NFR7.3 says tests must pass on Linux and Windows before a change is accepted. Python versions matter because the tool supports 3.10 and newer.

A. Linux and Windows, each with the oldest (3.10) and newest (3.12) Python
B. Linux and Windows with Python 3.12 only
C. Linux, Windows and macOS with 3.10 and 3.12
X. Other (please specify)

[Answer]: C

## Q3. How should the Linux program file be built?

Why we ask: requirement NFR7.2 says the Linux program must run on RHEL 8 and Ubuntu 20.04, so it must be built on a system as old as those, or it will refuse to start on them. GitHub's own Linux machines are newer than that.

A. Build inside a RHEL 8 compatible container (AlmaLinux 8) on the hosted Linux machine, then start the file on a clean Ubuntu 20.04 container to check it
B. Build on GitHub's newest Linux machine and accept that old systems may not work
C. Build on one of your own old Linux machines
X. Other (please specify)

[Answer]: X. Is there a way to use a build that can work on all OSs, for example Python.

Follow-up (answered in chat): a single file for all systems is not possible; chose "Both": program files built per system, plus an offline install pack per system for computers that have Python.

## Q4. Which build tool makes the program file?

Why we ask: PyInstaller was tried on your Mac and works. Nuitka makes a faster, more compact program but takes much longer to build and has not been tried.

A. PyInstaller only (the one that is tested)
B. PyInstaller, and also try Nuitka in a separate non-blocking job to compare
C. Nuitka only
X. Other (please specify)

[Answer]: A

## Q5. What must pass before a change can merge to `main`?

Why we ask: these are the quality gates. Each one blocks the merge if it fails.

A. Lint and format check (`ruff`), the full test suite on all systems, the program-file build with a smoke test (start it, print the version, run a pull-bundle-verify-unpack round trip)
B. Only the full test suite on all systems
C. A plus a check of dependencies for known security problems
X. Other (please specify)

[Answer]: A

## Q6. Where do the built program files go?

Why we ask: you carry them to the air-gapped side yourself, so they need a place you can fetch them from.

A. Attached to each CI run as downloadable files (kept for a limited time)
B. Attached to a GitHub release when you tag a version, and to each CI run
C. Uploaded to a file share or artifact store you name
X. Other (please specify)

[Answer]:B

## Q7. Should the download-speed benchmark run automatically?

Why we ask: requirement NFR1.1 (80% of connection speed) can only be measured on a real connection. A hosted machine's connection is not yours, so an automatic result would not mean much for you, but could catch a large slowdown.

A. No, keep it a manual command you run on your own connection
B. Yes, weekly on the hosted machine, reported but never blocking
X. Other (please specify)

[Answer]: A

## Q8. Should merges to `main` need a pull request?

Why we ask: your practice is short-lived branches merged by squash. The setting on GitHub that requires the checks to pass before merging belongs to you, so I will describe it rather than change it.

A. Yes: every change goes through a pull request and the checks must pass
B. No: you may push to `main` directly and the checks run afterwards
X. Other (please specify)

[Answer]:A
