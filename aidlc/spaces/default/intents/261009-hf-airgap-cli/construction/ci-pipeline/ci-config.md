# CI Configuration

## Choices

| Question | Decision |
|----------|----------|
| Service | GitHub Actions (Q1 A) |
| Test systems | Linux, Windows, macOS, each with Python 3.10 and 3.12 (Q2 C) |
| Linux program | Built in an AlmaLinux 8 container, started on Ubuntu 20.04; plus an offline install pack per system for computers with Python (Q3, "Both") |
| Build tool | PyInstaller only (Q4 A) |
| Gates | Lint and format, tests on all systems, program build with a full workflow run (Q5 A) |
| Files | Attached to each run, and to a GitHub release when a `v*` tag is pushed (Q6 B) |
| Speed benchmark | Manual only (Q7 A) |
| Merging | Pull request required, checks must pass (Q8 A) |

## Files

- `.github/workflows/ci.yml`: jobs `lint`, `test` (3 systems x 2 Pythons), `build-linux`,
  `run-linux-on-ubuntu-20-04`, `build-windows`, `offline-pack` (Linux and Windows x 2 Pythons).
  Runs on pull requests, on pushes to `main`, and when called by the release workflow.
- `.github/workflows/release.yml`: on a `v*` tag, runs `ci.yml`, then creates the release with the
  program files and zipped offline packs.
- `packaging/roundtrip_smoke.py`: drives a finished program file through key create, trust, pull
  (a 17 MB public model), bundle, verify, unpack, list, verify with a scrubbed environment.
- `packaging/offline_pack.py`: builds the wheels of the tool and its dependencies.

## Settings for you to make on GitHub (not changed by me)

1. Settings, Branches, rule for `main`: require a pull request; require status checks `lint`,
   `test`, `build-linux`, `run-linux-on-ubuntu-20-04`, `build-windows`, `offline-pack`; allow only
   squash merging (Settings, General, Pull Requests).
2. Settings, Actions, General: allow workflow runs; workflow permissions stay read-only (the
   release workflow asks for write itself).

## Known limits

- The pipeline has not run on GitHub yet; only the definitions are tested (`tests/test_ci_definition.py`)
  and the smoke script and offline pack were run locally on macOS arm64. Expect to fix small
  platform differences on the first real run (NFR7.1, NFR7.2, NFR7.3 stay unverified until then).
- Programs are 64-bit Intel/AMD only. The macOS test job checks the code, but no macOS program is
  published.
- The pull step of the smoke test needs the internet and Hugging Face; an outage fails the job.
