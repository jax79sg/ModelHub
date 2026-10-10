# modelhub

> [!NOTE]
> **About this project.** This is **jax79sg**'s means of learning and understanding the challenges of building software with a coding agent. **Much of this entire repository — the code, the tests and the documentation — was made with [Claude Code](https://claude.com/claude-code), using Anthropic's Claude Sonnet model.** The [`aidlc/`](aidlc/) folder keeps the trail: what was asked, what was decided and what was built, stage by stage.
>
> **How it was checked.** The tool is built behind automated tests (343 pass on a Mac; the checks on Linux and Windows have not run on GitHub yet). **No security scanning has been switched on** and no one has reviewed it independently; the breakdown, and what this is *not*, is in [How this was reviewed and hardened](#how-this-was-reviewed-and-hardened).

[![CI](https://github.com/jax79sg/ModelHub/actions/workflows/ci.yml/badge.svg)](https://github.com/jax79sg/ModelHub/actions/workflows/ci.yml)
[![Release](https://github.com/jax79sg/ModelHub/actions/workflows/release.yml/badge.svg)](https://github.com/jax79sg/ModelHub/actions/workflows/release.yml)

A command-line tool that downloads public Hugging Face models (files, README, metadata) on a computer with internet, packs them into signed pieces that fit on removable drives, and rebuilds them inside an air-gapped environment into a folder layout that a web app can read directly. The same program runs on Linux and Windows on both sides; the web app that reads the folders is a separate, later project.

```
online computer                              drives                 air-gapped computer
pull  ->  bundle (signed, split)  ->  carry  ->  verify  ->  unpack  ->  list
```

## How this was reviewed and hardened

Written down so a reader can judge it, including the parts that are not flattering. Figures are a snapshot of the repository on **10 October 2026**.

**Reviewed**

- **Approval gates, on the record.** The project follows a written workflow (AI-DLC): the intent, feasibility, requirements, contracts, non-functional requirements, code-generation plan, test instructions and CI plan were each written first and approved by jax79sg before the next step. Every request, answer and approval is logged in [`aidlc/spaces/default/intents/261009-hf-airgap-cli/audit/`](aidlc/spaces/default/intents/261009-hf-airgap-cli/audit/) (about 3,800 lines). Automated reviewer agents were turned off by jax79sg's instruction ("stop using sub-agents"), so the reviews were done by the same session that wrote the work.
- **Tests: 343** run without the internet, plus 6 that use the real Hugging Face Hub (run on request with `pytest -m network`). They were written before the code they test (the team's test-first practice). They include: a flipped byte in every kind of piece, killing the tool at every write point and running it again, memory use on a 1 GB file, a 10,000-folder store listed in under 5 seconds, 999,999 pieces accepted and one more refused, and the air-gapped commands run with the network blocked.
- **Bugs found by running it**, not by reading it: a damaged manifest crashed `verify`; stopping `unpack` early left stale pointers; a README with Windows line endings lost them; a packed program started helper processes wrongly. Each now has a test.
- **Measured download speed:** 0.94 of the connection's best speed on a 1 GB file (target 0.8), by hand with `tools/benchmark_download.py`. A first run reported 6.9 because the measuring method was wrong; it was fixed and re-run. This is one run on one connection.
- **Every requirement traced to code or a test:** [`traceability.json`](aidlc/spaces/default/intents/261009-hf-airgap-cli/construction/code-generation/traceability.json) maps 112 requirement IDs to a file, and a check confirms each file exists. That shows a test exists, not that the test is good.

**Hardened (in the tool)**

- Every bundle is signed (Ed25519). `verify` and `unpack` check the signature first and refuse a bundle that is unsigned, altered, or signed by a key this computer has not been told to trust. Trust needs the key's fingerprint typed in, received by a different route.
- Unpacking writes only inside the chosen folder: absolute paths, `..` and links in a bundle are refused.
- A Hugging Face token is read from `HF_TOKEN` or a hidden prompt, never from the command line, and never appears in a bundle, record, log or message (tested).
- The air-gapped commands (`verify`, `unpack`, `list`, `key`) make no network connection (tested with the network blocked). The tool never loads or runs a model file.
- Hugging Face usage reporting is switched off by default.

**What this is not**

- It has had **no independent security review or penetration test**. No dependency or code scanning, secret scanning or Dependabot is switched on yet, and the CI plan did not include a dependency scan.
- **The CI has not run on GitHub yet.** The workflow files are tested only as text; the Linux, Windows and macOS test runs, the old-Linux build and the release job are unproven until the first run. The Linux file has not been tried on RHEL 8 or Ubuntu 20.04, and the Windows file has not been built.
- **Everything was committed straight to `main`**; there have been no pull requests yet. The GitHub settings that would require them are described in [`ci-config.md`](aidlc/spaces/default/intents/261009-hf-airgap-cli/construction/ci-pipeline/ci-config.md) but not switched on.
- Memory and size targets were checked at 1 GB and by calculation, not with a real 500 GB or 1 TB file.
- It is a tool for moving **public** models only; private and gated models are refused. Treat it as a learning project.

## What it does

- **Choose what to fetch:** `pull` first lists a model's files grouped by type (safetensors, gguf, onnx, and so on) with sizes, and downloads nothing until you pick types with `--type`. Settings files, the README and the licence are always kept.
- **Fast, restartable downloads:** uses Hugging Face's own library with several connections at once. Stop it at any moment and run it again; verified files are not fetched again. Rate limits and network errors are retried with waits of 1, 2, 4, 8 and 16 seconds.
- **Everything the model page needs:** README (with a second copy whose outside pictures are stored locally, up to 7 MB each), summary details, file list with checksums and safety-scan results, history, and branches and tags, kept as Hugging Face returned them with the capture time.
- **Split to fit your drives:** `bundle` cuts a model into plain pieces of a size you set (below 1 GB if needed), or fills drives one at a time with `--interactive`. A damaged piece is replaced alone; no other piece is copied again.
- **Signed and checked:** each bundle has a description file and a signature; `verify` names every missing or damaged piece, not just the first.
- **Rebuilt for a web app:** `unpack` puts the model into a fixed folder layout (the model store) with plain-text `latest` and `refs/<name>` pointer files, no links, so it works on Linux and Windows.
- **Lists what you have:** `list` shows name, commit, capture date, size and licence for every model in a store.
- **Progress and records:** live progress for anything over 2 seconds; a run record of what was fetched, skipped and failed; exit status 0, 1 (an item failed) or 2 (could not run).
- **Delivered three ways:** a single program file per system (no Python needed), an offline install pack for computers with Python, or `pip install`.

## Architecture

One Python package, `src/modelhub/`, with a small command layer over single-purpose modules:

| Module | Role | Talks to |
|---|---|---|
| `cli.py` | The commands: `pull`, `bundle`, `verify`, `unpack`, `list`, `key` | the modules below |
| `hubclient.py`, `download.py`, `pull.py` | Hugging Face access, multi-connection downloads, retries, the download record | Hugging Face (online side only) |
| `filetypes.py`, `record.py`, `summary.py`, `readme_assets.py` | File grouping, record layout, model-page details, README pictures | the download record |
| `bundle.py`, `pieces.py` | Cutting a record into pieces, sizing, drive-by-drive mode | the download record, signing keys |
| `signing.py`, `verify.py`, `unpack.py`, `store.py` | Keys and trust, checks, safe rebuild, the model store and `list` | the pieces, the model store |
| `fsutil.py`, `progress.py`, `runrecord.py`, `logsetup.py`, `redact.py` | Safe file writes, locking, progress, run records, logs, hiding secrets | local disk |

Only the `pull` step uses the network. The three formats between the steps are fixed contracts, written in [`contract-summary.md`](aidlc/spaces/default/intents/261009-hf-airgap-cli/inception/contract-design/contract-summary.md): the download record, the bundle, and the model store. Full design rationale and decision history: [`aidlc/`](aidlc/).

## Prerequisites

- **Online computer:** Python 3.10 or newer (or the program file), internet access to Hugging Face, and disk space for the model plus the pieces.
- **Air-gapped computer:** the program file for your system, or Python 3.10+ with the offline install pack. No internet is needed or used.
- **Both sides:** a way to carry the pieces (removable drives) and a separate way to send one short fingerprint (phone, chat, paper) so the air-gapped side can trust your signing key.
- Linux or Windows, 64-bit Intel/AMD. macOS runs the code but no macOS program file is published.

## Quick Start

### 1. Install

```bash
pip install .            # needs Python 3.10 or newer
modelhub --version
```

Where Python is not available, use the single program file for your system (`modelhub-linux-x86_64`, `modelhub-windows-x86_64.exe`) from the GitHub release. Where Python 3.10+ is available but there is no internet, use the offline pack for your system and Python version (`modelhub-pack-<system>-py<version>.zip` from the release), unzipped:

```bash
pip install --no-index --find-links <unzipped-folder> modelhub
```

### 2. Once: make a signing key (online side) and trust it (air-gapped side)

```bash
modelhub key create                          # prints the key id and fingerprint
modelhub key export <key-id> --out modelhub-public.key
```

Carry `modelhub-public.key` to the air-gapped side. Send its **fingerprint by a different route**. On the air-gapped computer:

```bash
modelhub key trust modelhub-public.key       # asks you to type the fingerprint
modelhub key list
```

A bundle signed by a key that is not trusted is refused.

### 3. Download (online)

```bash
modelhub pull org/name                       # shows the file types found; downloads nothing yet
modelhub pull org/name --type safetensors --type json
modelhub pull --list models.txt --type all   # one model id per line, # for comments
```

Each model lands in `pulled/models/<id>/commits/<commit>/`. A token for gated models is not supported; `HF_TOKEN` or `--ask-token` only raises rate limits.

### 4. Pack for the drives (online)

```bash
modelhub bundle pulled/models/org/name/commits/<commit> --out outgoing --piece-size 900MB
modelhub bundle <record> --out outgoing --interactive    # fill drives one at a time
```

This writes plain pieces plus a `.bundle.json` and a `.bundle.sig` signature file. Copy the whole folder (or spread the pieces across drives, keeping the two small files with the first).

### 5. Check and rebuild (air-gapped)

```bash
modelhub verify /media/drive1 /media/drive2          # signature and every piece
modelhub unpack /media/drive1 /media/drive2 --store /srv/models
modelhub list /srv/models
modelhub verify /srv/models                          # re-check every file of the store later
```

The store holds `models/<id>/commits/<commit>/{files,raw,readme,manifest.json,summary.json}` plus `latest` and `refs/<name>` text files naming a commit.

### Recovering by hand

Pieces are plain slices of one tar file; the signature file lists their names and checksums.

```bash
cat name.part-000001 name.part-000002 > name.tar          # Linux
```
```
copy /b name.part-000001+name.part-000002 name.tar        (Windows)
```

## Stopping / Resetting

Stop any command with Ctrl-C at any moment and run it again; it continues from the verified work. Only one run may use an output folder at a time. To start over, delete the output folder (`pulled`, the pieces folder, or the store).

## Configuration Reference

There is no config file. The few settings:

- **`HF_TOKEN`** — optional Hugging Face token (or `--ask-token` for a hidden prompt). Never accepted on the command line.
- **`MODELHUB_HOME`** — where signing keys and trusted keys are kept (default `~/.modelhub`). Use two different folders to try both sides on one computer.
- **`--workers`** — files downloaded at once (default 8).
- **`--piece-size`** — largest piece, for example `900MB`; the smallest accepted is documented in the code and is far below 1 GB.
- **`--verbose` / `--debug`** — also write `modelhub.log` beside the output.
- `HF_HUB_DISABLE_TELEMETRY` and the update check are switched off by default.

## Development

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                       # real-network tests are skipped; run them with: pytest -m network
ruff check . && ruff format --check .
python tools/benchmark_download.py org/model big-file.bin   # speed check against the link (80%)
```

### Build the program file

```bash
pip install -e ".[build]"
python packaging/build.py pyinstaller
python packaging/roundtrip_smoke.py dist/modelhub-<system>-x86_64   # runs the whole workflow
python packaging/offline_pack.py                                    # the offline install pack
```

The checks in `.github/workflows/ci.yml` do this on every pull request; pushing a tag such as `v1.0.0` runs them and then attaches the files to a GitHub release.

Full instructions: [`aidlc/spaces/default/intents/261009-hf-airgap-cli/construction/build-and-test/`](aidlc/spaces/default/intents/261009-hf-airgap-cli/construction/build-and-test/).

## Troubleshooting

**`verify` or `unpack` refuses the bundle because its key is not trusted** — this computer has not trusted the key. Run `modelhub key trust` with the public key file and type the fingerprint you received separately.

**`verify` names a missing or damaged piece** — copy just that piece again from the source and run `verify` again; no other piece needs copying.

**`pull` says a model is not found, or is private or gated** — the Hub reports the same answer for all three; only public models are supported.

**"another run is using <folder>"** — a second `modelhub` is running on the same output folder, or an earlier one is still open. Close it, or wait. A run that was killed releases the folder by itself.

**The program file will not start on an old Linux** — it must be built on RHEL 8 or older; the CI does this, a build on a newer system will not run there.

## Project Structure

```
src/modelhub/          The package: commands and modules (see Architecture)
tests/                 343 tests (+6 against the real Hub); conftest.py holds a fake Hugging Face
packaging/             Program-file build, offline install pack, whole-workflow smoke script
tools/                 benchmark_download.py — the manual download-speed check
.github/workflows/     ci.yml (checks and builds) and release.yml (publish on a v* tag)
aidlc/                 Design docs, requirements, decision history, audit trail
pyproject.toml         Dependencies, version, ruff and pytest settings
```
