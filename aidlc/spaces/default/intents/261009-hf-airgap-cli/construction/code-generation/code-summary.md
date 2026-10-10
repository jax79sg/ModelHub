# Code Summary

## What was built

The `modelhub` command (version 0.2.0), replacing the earlier prototype (`hub.py`, `manifest.py` and
its round-trip test were removed).

| Command | Does | Main modules |
|---------|------|--------------|
| `pull` | Lists file types, downloads chosen types with several connections, keeps README, metadata, pictures; restartable | `pull.py`, `download.py`, `hubclient.py`, `filetypes.py`, `readme_assets.py`, `summary.py`, `record.py` |
| `bundle` | Checks a download record, cuts it into plain pieces (fixed size or drive by drive), signs it | `bundle.py`, `pieces.py`, `signing.py` |
| `verify` | Checks signature first, then every piece; or every file of a store; names all problems | `verify.py` |
| `unpack` | Rebuilds into the model store, refusing unsafe entries, repairing `latest`/`refs` pointers | `unpack.py`, `store.py` |
| `list` | Name, commit, capture date, size, licence for each model | `store.py` |
| `key` | create, export, fingerprint, trust, untrust, list | `signing.py` |

Shared: `fsutil.py` (atomic writes, safe paths, run lock, Windows/case checks), `redact.py`,
`progress.py`, `runrecord.py`, `logsetup.py`. Packaging: `packaging/entry.py`, `packaging/build.py`.
Tools: `tools/benchmark_download.py` (NFR1.1 speed check, run by hand on a real connection).

## Tests

334 tests pass without internet; 6 real-network tests (`pytest -m network`) are kept apart. Written
test-first per `team.md`. Notable boundary tests: a byte flipped in every position class
(tamper regression), killing the tool at every write point (restart), memory ceiling and 1 GB sparse
file checks, listing 10,000 version folders, network blocked for the air-gapped commands, secrets
scan of every output. `ruff check` and `ruff format --check` are clean.

## Deviations and findings

- **D1** The prototype's single-tar bundle was replaced by plain pieces plus signed description
  (contract C2), so a damaged piece is replaced alone.
- **T4** Speed against the link (NFR1.1) is a hand-run benchmark, not part of the normal suite;
  no real-connection result has been recorded yet.
- Found by tests and fixed: malformed manifest crashed `verify`; `unpack` stopped early left stale
  pointers; README CRLF lost on text read; BOM in manifest; PyInstaller helper processes needed
  `freeze_support()`.
- Packaging experiment: PyInstaller one-file build works on macOS arm64 and passes the full
  workflow with a scrubbed environment. Linux (old system), Windows, and Nuitka builds are left to
  the CI Pipeline stage; the signing public key is typed in by fingerprint on arrival (NFR2.7).
- Only x86-64 is targeted for Linux and Windows.

## Traceability

`traceability.json` maps every `FR`, `NFR` and detailed `NFRx.y` ID to an implementing or testing
file; the traceability sensor passes.
