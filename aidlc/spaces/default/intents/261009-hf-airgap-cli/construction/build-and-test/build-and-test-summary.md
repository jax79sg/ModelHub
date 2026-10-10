# Build And Test Summary

## Status

- Build: success (PyInstaller one-file, macOS arm64, smoke check `modelhub 0.2.0`).
- Tests: 334 passed, 6 real-network tests deselected; `ruff check` and `ruff format --check` clean.
- Readiness: build-ready yes; test-ready yes; deployment-ready no, pending the CI Pipeline stage
  (Linux and Windows builds, tests on both systems).
- Instruction files: build, integration, performance, security (this folder); unit test
  instructions are in `code-generation/`.

## Target Verification Matrix

| Target ID | Source | Expected | Actual | Evidence | Owning Stage | Verdict |
|-----------|--------|----------|--------|----------|--------------|---------|
| NFR1.1 | performance-requirements | tool >= 0.8 x link | 0.94 (30.4 vs 32.4 MB/s, 1 GB) | `benchmark-result.json` | build-and-test | Met |
| NFR1.2 | performance-requirements | 8 transfers at once by default | 8 | `tests/test_download.py` | build-and-test | Met |
| NFR1.3 | performance-requirements | at most 8 GB for any size | about 23 MB peak on 1 GB; 500 GB not run | `tests/test_memory_limits.py` | build-and-test | Met (scaled test) |
| NFR1.4 | performance-requirements | 2 GB checked under 256 MB | 1 GB checked, small footprint | `tests/test_memory_limits.py` | build-and-test | Met (scaled test) |
| NFR1.5 | performance-requirements | progress every 2 s / 30 s | as specified | `tests/test_progress.py` | build-and-test | Met |
| NFR1.7 | performance-requirements | list of 10,000 folders in 5 s | under 5 s | `tests/test_scale.py` | build-and-test | Met |
| NFR1.8 | performance-requirements | verify time within 10% of store size | store not consulted | `tests/test_scale.py` | build-and-test | Met |
| NFR1.9 | scalability-requirements | 1 TB file within 8 GB | planned without reading; not run at 1 TB | `tests/test_scale.py` | build-and-test | Met (scaled test) |
| NFR1.10 | scalability-requirements | 999,999 pieces ok, one more refused | as specified | `tests/test_scale.py` | build-and-test | Met |
| NFR4.4 | scalability-requirements | recheck reads only replaced pieces | as specified | `tests/test_verify.py` | build-and-test | Met |
| NFR7.3 | reliability-requirements | tests pass on Linux and Windows | macOS only so far | none yet | ci-pipeline | Unverified |

## Outstanding items

- NFR7.3 (all tests on Linux and Windows) is owned by the CI Pipeline stage, which is scheduled
  next. It stays `Unverified` here and is surfaced at the approval gate.
- NFR1.3, NFR1.4 and NFR1.9 were checked at 1 GB and by planning, not at 500 GB or 1 TB.
