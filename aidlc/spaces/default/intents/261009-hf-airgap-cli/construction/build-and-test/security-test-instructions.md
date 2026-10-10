# Security Test Instructions

## Automated

- Tamper: `tests/test_tamper_regression.py` flips bytes in pieces, manifest and signature.
- Signing and trust: `tests/test_signing.py`, `tests/test_trust.py` (untrusted key refused).
- Unsafe archive entries: `tests/test_unpack_safety.py` (`..`, absolute paths, links).
- Secrets: `tests/test_secrets.py`, `tests/test_token.py` (token never in output, record or log).
- Offline: `tests/test_offline.py`.

## Run

```bash
.venv/bin/pytest tests/test_tamper_regression.py tests/test_signing.py tests/test_trust.py tests/test_unpack_safety.py tests/test_secrets.py tests/test_token.py tests/test_offline.py -q
```

No SAST tool is configured; `ruff` runs its default rules. Dependency vulnerability scanning is
for the CI Pipeline stage.
