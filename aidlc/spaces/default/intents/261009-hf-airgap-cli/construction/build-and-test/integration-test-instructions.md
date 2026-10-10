# Integration Test Instructions

## Boundaries covered

| Boundary | Test file |
|----------|-----------|
| pull to bundle to verify to unpack to list, end to end | `tests/test_slice_roundtrip.py`, `tests/test_bundle_cli.py` |
| Hugging Face client (fake hub, and the real one) | `tests/conftest.py` (FakeHub), `tests/test_hubclient_network.py` |
| Drives one at a time, any order, damaged piece replaced alone | `tests/test_interactive_drives.py`, `tests/test_verify.py` |
| Stopped at every write point and restarted | `tests/test_kill_restart.py` |
| Air-gapped commands with the network blocked | `tests/test_offline.py` |

## Run

```bash
.venv/bin/pytest -q                  # normal suite, no internet (334 tests)
.venv/bin/pytest -m network -q       # 6 tests against the real Hub; needs internet
```

Test data is created by the fixtures; nothing outside `tmp_path` is touched.
