# Tech Stack Decisions

Inputs: `requirements.md`, `contract-summary.md`, `team-practices` (test-driven; `ruff`; trunk-based), the feasibility findings, and your answers in `nfr-requirements-questions.md`. "Decided" means settled by your answers or by existing facts. "Pending" means a choice that must be settled by a test, with its criteria.

## Decisions

| # | Area | Decision | Status | Why | Alternatives considered |
|---|------|----------|--------|-----|------------------------|
| T1 | Language | Python. Build with 3.12; the package supports 3.10 or newer | Decided | You work in Python (feasibility Q7); the official Hugging Face library covers everything needed, including the fast-transfer part; an existing prototype uses it | JavaScript, Rust, Go: not among your skills, and Go has no official library (see `feasibility-assessment.md`) |
| T2 | Command-line framework | Typer (already used), with its Rich display for progress | Decided | Already in the prototype; fits NFR1.5 progress display | Plain `argparse`: more code for the same result |
| T3 | Hugging Face access | The official `huggingface_hub` library with its fast-transfer component `hf_xet`; versions pinned and the pinned versions recorded in each bundle | Decided | Requirements FR5.1 (no scraping); the retired add-on `hf_transfer` is not used (CT-6); risk R4 | Raw HTTP calls: more code and more risk when Hugging Face changes things |
| T4 | README pictures | The HTTP client already installed with `huggingface_hub` | Decided | No new dependency; supports time limits (NFR5.3) | A second HTTP library: another thing to package |
| T5 | Checksums | SHA-256 from the Python standard library | Decided | Matches the checksum Hugging Face reports (NFR2.2) | Other hashes: would not match Hugging Face |
| T6 | Archive and slicing | The Python standard library `tarfile` in POSIX pax format, uncompressed, cut into slices | Decided | Contract C2 and your answer Q6 A: pieces can be rejoined by hand and opened with standard tools | Zip, custom format: harder to open by hand |
| T7 | Signatures | The `cryptography` package, Ed25519 signatures, 32-byte keys | Provisional | Q4 B; Ed25519 is small, fast and widely reviewed; the package is not in the project yet, so the packaging test must prove it works inside the program file | PyNaCl (also a native library); a pure-Python signer (slower, less reviewed) |
| T8 | One program file per system | PyInstaller or Nuitka, chosen by a short test build on both systems | Pending (your answer Q7 C) | See the test below | Shipping Python itself: not allowed, since the air-gapped side has no Python |
| T9 | Tests | `pytest`; saved copies of Hugging Face responses for repeatable tests; a `network` marker for the few real-network tests | Decided | Requirements NFR8; `team-practices` | None needed |
| T10 | Code checks | `ruff` for checking and formatting, line length 100 | Decided | `team-practices` | None needed |
| T11 | Where checks run | Not decided here | Pending | You said "another service or own machine" and have a GitHub repository; Linux and Windows both must be covered (NFR7.3). The later check-setup step decides | GitHub-hosted runners; your own machines |

## T8 Test Build (the packaging choice)

Both tools build the same small program that imports `typer`, `huggingface_hub`, `hf_xet` and `cryptography`. The test runs on Windows (10 or newer) and on Linux (built on a RHEL 8-compatible system, NFR7.2). The choice is made on these criteria, in order:

1. The file starts on a computer with no Python and prints its version (FR8.1).
2. Downloading a small public model works, so the fast-transfer part is bundled correctly.
3. Creating and checking a signature works, so the `cryptography` native code is bundled correctly.
4. Starting time under 5 seconds and file size reported (no limit set; reported so you can judge).
5. Whether Windows security software or a Linux scanner flags the file; packaging tools that unpack themselves are sometimes flagged, which matters for your approval step (feasibility Q2).

If neither tool passes 1 to 3 on both systems, the fallback is a folder of files zipped together instead of one file, and that would need your decision because Q7 B asked for a single file.

## Dependencies To Add

- `cryptography` (T7). Everything else is already installed or in the Python standard library.
- A packaging tool for builds only (T8), kept out of the tool's normal dependencies.

## Open Items

- Final choice for T8, and the system that runs the checks (T11).
- The exact key file layout, settled when the key commands are designed.
