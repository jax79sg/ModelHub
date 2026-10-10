# Security Requirements

Derived from `requirements.md` (NFR2, NFR5, NFR6) and your answers in `nfr-requirements-questions.md` (Q3, Q4, Q10). Threats considered: damaged copies, a bundle altered on the way, a hostile README or picture, and a leaked access token.

## Authentication And Authorization

- The tool has no accounts and no login of its own. The only credential is an optional Hugging Face access token (NFR6). Private and gated models are out of scope (`intent-statement`).
- The signing key (NFR2.3 and after) is the only other secret. Whoever holds the private key can make bundles that the air-gapped side will trust.

## Requirements

| ID | Requirement | Pass criterion | Source |
|----|-------------|----------------|--------|
| NFR2.1 | A change of one byte in any piece, fetched file, manifest or signature is detected | A test that flips one byte at a time in each kind of file is always caught by `verify` | Requirements NFR2 |
| NFR2.2 | Checksums are SHA-256. Where Hugging Face reports a checksum, it is compared too | A file whose Hugging Face checksum differs is reported failed | Requirements FR5.4 |
| NFR2.3 | Each bundle's manifest is signed with a private key that you keep (digital signature) | A bundle produced by `bundle` carries a signature file next to the manifest | NFR questions Q4 B |
| NFR2.4 | `verify` and `unpack` refuse a bundle whose signature is missing, invalid, or made by a key this side does not trust, and say which | Each of the three cases ends with status 1 and a message naming the cause, and nothing is rebuilt | Q4 B |
| NFR2.5 | A command creates the key pair on the download side. The private key is stored in a file only the owner can read and is never written into a bundle, run record or message. The public half is exported as a separate small file | After `key create`, the private key file is owner-only (Linux mode 600; Windows owner-only access) and no bundle in a test run contains its bytes | Q4 B; NFR6 |
| NFR2.6 | The tool shows a short, readable fingerprint of a public key on both sides, so a person can compare them | The same key gives the same fingerprint on Linux and Windows | Q10 A, and your question "can we use the same tool to check on arrival" |
| NFR2.7 | On the air-gapped side a public key becomes trusted only after a person confirms the fingerprint at the keyboard. The confirmation is recorded | A trust command without that confirmation does not trust the key | Q10 A |
| NFR2.8 | The public key comes across separately from the bundles, once, by the approved route. It is never taken from a bundle being checked | A bundle that carries its own public key is still refused if that key is not already trusted | Q10 A (a key inside the bundle protects nothing) |
| NFR2.9 | When the key is replaced or lost, a new pair is made and trusted again through NFR2.6 to NFR2.8. Bundles signed by a retired key verify only while that key is still trusted | After removing trust for a key, bundles signed by it fail with a clear message | Q4 B; open question in `contract-summary.md` |
| NFR2.10 | Unpacking writes only inside the chosen output folder. An entry that would escape it (absolute path, `..`, a link outside) is rejected, and total output may not exceed the size the signed manifest declares | Test archives with `../x`, absolute paths and links outside are rejected; a stream longer than declared stops early | Corner checklist (files and paths; hostile input) |
| NFR5.1 | `verify`, `unpack`, `list` and the key commands make no network connection | The test suite runs them with all network access blocked and they pass | Requirements NFR5; FR7.6 |
| NFR5.2 | The program file contains everything it needs; it downloads nothing at run time and does no update check or usage reporting | With the network blocked, every command except `pull` works from a fresh install | Requirements NFR5 |
| NFR5.3 | On the download side, the only network use is to Hugging Face hosts for the requested downloads and to README picture addresses (`http` or `https`). Each picture is limited to 7 MB, and every request has a 30-second time limit | A picture larger than 7 MB is skipped and listed; a request that stalls is stopped after 30 seconds | NFR questions Q3 (7 MB); corner checklist (network) |
| NFR6.1 | An access token never appears in a bundle, run record, log, message or error text | A test run with a recognisable fake token finds it in no output file or message | Requirements NFR6 |
| NFR6.2 | The token is read from the `HF_TOKEN` environment variable or a hidden prompt. It is not accepted on the command line, so it stays out of shell history, and the tool never stores it | A token given as a command-line option is rejected with an explanation | Requirements NFR6; derived (assumption: command-line tokens are leak-prone) |
| NFR6.3 | The library's usage reporting (telemetry) is switched off by default | A run makes no connection to any host outside Hugging Face and README picture addresses | `feasibility-assessment.md` E8 (setting `HF_HUB_DISABLE_TELEMETRY`) |
| NFR6.4 | The tool never runs, loads or imports a model file. It only copies, slices and checks the bytes. The README and Hugging Face responses are treated as data and never executed | No code path imports a model file; a test model file containing a script runs nothing | Requirements Q1; `feasibility-assessment.md` (pickle risk) |

## Contract Additions Caused By These Requirements

The signature (Q4 B) adds to the contract in `contract-summary.md`. This is recorded here so Code Generation builds it:

- C2 gains a signature file `<same stem>.bundle.sig` beside the manifest, and the manifest records the `key_id` (fingerprint) of the signing key.
- C4 gains a `key` command group: create a key pair, export the public key, show a fingerprint, trust a key (with the confirmation in NFR2.7), and untrust a key.
- `format_version` of the bundle moves to a minor increase for the added fields, as the change rules in the contract allow.

## Threat Notes

- The content scan and approval you described (feasibility Q2) stays the main defence against bad model files. The signature protects against change in transit and does not judge what a model contains.
- Hugging Face's own safety-scan results are kept as information (FR3.3). They are a third party's view at one moment, not a guarantee.
