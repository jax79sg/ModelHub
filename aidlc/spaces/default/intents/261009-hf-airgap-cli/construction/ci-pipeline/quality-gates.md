# Quality Gates

## Gates before a change merges to main

| Gate | Command | Where | Blocks merge |
|------|---------|-------|--------------|
| Lint | `ruff check .` | `lint` | yes |
| Format | `ruff format --check .` | `lint` | yes |
| Tests | `pytest -q` (334+ tests, no internet) | `test`, 6 systems | yes |
| Linux program builds and works | `packaging/build.py pyinstaller`, then `packaging/roundtrip_smoke.py` | `build-linux` | yes |
| Linux program works on Ubuntu 20.04 | `packaging/roundtrip_smoke.py` | `run-linux-on-ubuntu-20-04` | yes |
| Windows program builds and works | same | `build-windows` | yes |
| Offline pack installs and starts | `pip install --no-index --find-links pack modelhub`, `modelhub --version` | `offline-pack` | yes |

These are the same commands that Build and Test ran (`build-instructions.md`,
`test-results.md`), so what passed on the developer computer is what is enforced.

## Not gated

- Download speed (NFR1.1): manual, `tools/benchmark_download.py`, on a real connection.
- Real-network tests (`pytest -m network`): manual.
- Dependency vulnerability scan: not chosen (Q5 A).
- Coverage percentage: none by team practice.

## Requirements this closes

NFR7.3 (tests pass on Linux and Windows) and NFR7.2 (Linux file built on an old system) are enforced
by the jobs above once the pipeline has run on GitHub.
