# Build Instructions

## Setup

```bash
python3.12 -m venv .venv                  # Windows: .venv\Scripts\...
.venv/bin/pip install -e ".[dev,build]"   # Python 3.10 or newer is supported
```

No environment variables or services are needed. `HF_TOKEN` is optional (higher rate limits).

## Build

```bash
.venv/bin/python packaging/build.py pyinstaller   # one program file in dist/, then a smoke check
```

Result on macOS arm64: `dist/modelhub-darwin-arm64`, smoke check printed `modelhub 0.2.0`. Linux
(oldest supported system) and Windows builds, and the Nuitka alternative, run in the CI Pipeline
stage.

## Verification and troubleshooting

- Lint and format: `.venv/bin/ruff check . && .venv/bin/ruff format --check .`
- A packed program that fails with `-B` errors is missing `multiprocessing.freeze_support()` in
  `packaging/entry.py`; compiled parts to include are `hf_xet` and `cryptography`.
- `dist/`, `build/` are ignored by git.
