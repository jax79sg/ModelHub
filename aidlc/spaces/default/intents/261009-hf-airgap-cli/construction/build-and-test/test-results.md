# Test Results

## Commands run

| Command | Result |
|---------|--------|
| `python packaging/build.py pyinstaller` | success, `modelhub 0.2.0` |
| `.venv/bin/pytest -q` | 334 passed, 6 deselected, 0 failed |
| `.venv/bin/ruff check .` and `ruff format --check .` | clean |
| `tools/benchmark_download.py Qwen/Qwen2.5-0.5B model.safetensors` | ratio 0.94, target 0.8, passed |

## Notes

- A first benchmark run reported 6.9 because the fast-transfer route writes in bursts and the
  best 5 s window overstated the tool's rate. The tool now reports whole-transfer average; the
  second run is the one recorded (`benchmark-result.json`).
- Coverage is not measured; the team has no percentage floor (`team.md`).
