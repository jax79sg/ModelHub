# modelhub

> [!NOTE]
> **About this project.** This is **jax79sg**'s means of learning and understanding the challenges of building software with a coding agent. **Much of this entire repository — the code, the tests and the documentation — was made with [Claude Code](https://claude.com/claude-code), using Anthropic's Claude Sonnet model.** The [`aidlc/`](aidlc/) folder keeps the trail: what was asked, what was decided and what was built, stage by stage.
>
> **How it was checked.** The tool is built behind automated tests (369 on Linux and macOS; 363 on Windows, where 6 cannot run; all pass in GitHub Actions). The web app in [`web/`](web/) has 24 more tests of its own, run on all three systems. Automated scanning is on (CodeQL, GitHub secret scanning and Dependabot, GitGuardian), but **no one has reviewed it independently**; the breakdown, and what this is *not*, is in [How this was reviewed and hardened](#how-this-was-reviewed-and-hardened).

[![CI](https://github.com/jax79sg/ModelHub/actions/workflows/ci.yml/badge.svg)](https://github.com/jax79sg/ModelHub/actions/workflows/ci.yml)
[![Release](https://github.com/jax79sg/ModelHub/actions/workflows/release.yml/badge.svg)](https://github.com/jax79sg/ModelHub/actions/workflows/release.yml)

A command-line tool that downloads public Hugging Face models (files, README, metadata) on a computer with internet, packs them into signed pieces that fit on removable drives, and rebuilds them inside an air-gapped environment into a folder layout that a web app can read directly. The same program runs on Linux, Windows and (Apple Silicon) Mac on both sides. A small web app in [`web/`](web/) reads that folder and shows the models the way [huggingface.co/models](https://huggingface.co/models) does, with no internet needed.

```
online computer                              drives                 air-gapped computer
pull  ->  bundle (signed, split)  ->  carry  ->  verify  ->  unpack  ->  list
                                                                    |
                                                                    +-->  web app (web/): browse, search, read model cards
```

## How this was reviewed and hardened

Written down so a reader can judge it, including the parts that are not flattering. Figures are a snapshot of the repository and its GitHub settings on **11 October 2026**.

**Reviewed**

- **Approval gates, on the record.** The project follows a written workflow (AI-DLC): the intent, feasibility, requirements, contracts, non-functional requirements, code-generation plan, test instructions and CI plan were each written first and approved by jax79sg before the next step. Every request, answer and approval is logged in [`aidlc/spaces/default/intents/261009-hf-airgap-cli/audit/`](aidlc/spaces/default/intents/261009-hf-airgap-cli/audit/) (about 4,000 lines). Automated reviewer agents were turned off by jax79sg's instruction ("stop using sub-agents"), so the reviews were done by the same session that wrote the work.
- **Tests: 369** run without the internet (on Windows 6 of them are skipped because they test things Windows cannot do), plus 6 that use the real Hugging Face Hub (run on request with `pytest -m network`). They were written before the code they test (the team's test-first practice). They include: a flipped byte in every kind of piece, killing the tool at every write point and running it again, memory use on a 1 GB file, a 10,000-folder store listed in under 5 seconds, 999,999 pieces accepted and one more refused, and the air-gapped commands run with the network blocked.
- **Bugs found by running it**, not by reading it: a damaged manifest crashed `verify`; stopping `unpack` early left stale pointers; a README with Windows line endings lost them; a packed program started helper processes wrongly. Each now has a test.
- **Measured download speed:** 0.94 of the connection's best speed on a 1 GB file (target 0.8), by hand with `tools/benchmark_download.py`. A first run reported 6.9 because the measuring method was wrong; it was fixed and re-run. This is one run on one connection.
- **Web app: designed from evidence, tested with real data.** Its pages were worked out by pointing [REA](https://github.com/morluto/rea) at huggingface.co/models ([notes and screenshots](docs/reverse-engineering/)). It has **24 tests** against a made-up store, and it was also run against a store built by this tool's own pull, bundle, verify and unpack from four small public models; that is how odd real data (a licence given as a list, a missing README, files the Hub lists but that were never downloaded, a download-cache folder inside `files/`) was found. Looked at by eye in dark and light themes; phone widths were not tried on a phone.
- **Every requirement traced to code or a test:** [`traceability.json`](aidlc/spaces/default/intents/261009-hf-airgap-cli/construction/code-generation/traceability.json) maps 112 requirement IDs to a file, and a check confirms each file exists. That shows a test exists, not that the test is good.

**Hardened (in the tool)**

- Every bundle is signed (Ed25519). `verify` and `unpack` check the signature first and refuse a bundle that is unsigned, altered, or signed by a key this computer has not been told to trust. Trust needs the key's fingerprint typed in, received by a different route.
- Unpacking writes only inside the chosen folder: absolute paths, `..` and links in a bundle are refused.
- A Hugging Face token is read from `HF_TOKEN` or a hidden prompt, never from the command line, and never appears in a bundle, record, log or message (tested).
- The air-gapped commands (`verify`, `unpack`, `list`, `key`) make no network connection (tested with the network blocked). The tool never loads or runs a model file.
- Hugging Face usage reporting is switched off by default.

**Hardened (in the web app)**

- A model card (README) is treated as hostile text: scripts, styles, iframes, forms, event handlers and `javascript:` links are removed, and pictures that point to the internet are replaced by their alt text, so nothing is requested from outside. Every page carries a strict Content-Security-Policy.
- Files are never rendered by the site: they are served as downloads or as plain text, so an HTML or SVG file inside a model cannot run in the site's address. Paths are checked (`..`, encoded `..`, absolute paths, a link that leaves the folder, and the downloader's `.modelhub-dl/` cache are all refused; tested), and only files named in the store's own `summary.json` can be served.
- It listens on `127.0.0.1` by default and has no login. It only reads the store and never writes to it.

**What this is not**

- It has had **no independent security review or penetration test**. Automated scanning is switched on in GitHub: CodeQL (Python and the workflow files, on every pull request and weekly), GitHub secret scanning with push protection, Dependabot alerts and security updates, and a GitGuardian check on pull requests. On 11 October 2026 GitHub showed **0 alerts** from any of them. That is the scanners' verdict, not proof: they find known patterns, and the web app's six dependencies are not pinned or audited. Dependabot version updates and a dependency scan inside the CI are not set up.
- **The CI first ran on 10 October 2026 and failed on Windows**: a real bug (plain file names refused as escaping their folder, when Windows spelled the folder differently) and several tests that assumed Linux or macOS behaviour. These are fixed and the checks now pass on Linux, Windows and macOS with Python 3.10 and 3.12. The Linux file was built in an AlmaLinux 8 container and started on Ubuntu 20.04; it has not been tried on a real RHEL 8 machine. Version 1.0.0 was released on 10 October 2026 (Linux and Windows files and offline packs); 1.1.0 adds the Mac file. Version 1.1.1 (naming a key by its fingerprint) is merged but not released yet.
- **The first version was committed straight to `main`.** Since then every change has gone through a pull request: a ruleset on `main` requires a pull request, squash merging only, and the required checks to pass. No independent person has reviewed any of it; each pull request was merged on the project owner's instruction.
- Memory and size targets were checked at 1 GB and by calculation, not with a real 500 GB or 1 TB file.
- **The web app is newer and less checked than the tool.** Its 24 tests run in CI on Linux, Windows and macOS with Python 3.10 and 3.12, but they were written alongside the code by the same author. Its six dependencies (FastAPI, uvicorn, Jinja2, markdown-it-py, mdit-py-plugins, nh3) are installed at their newest versions, are not pinned and were not audited. Its sanitiser and path checks are tested against the attacks its author thought of, not an attacker's. Only small models were tried; the whole store is read into memory, which has not been timed on thousands of models.
- **The web app is not the real site.** Trending, inference widgets and providers, Spaces, community discussions, likes, sign-in and the model tree are not reproduced; the store holds nothing to build them from. Downloads and likes are a snapshot from the day each model was pulled.
- It is a tool for moving **public** models only; private and gated models are refused. Treat it as a learning project.

## How much Claude Code was used

This project was built with Claude Code, so the amount of Claude Code used is tracked and kept with the code. [`tools/claude_usage.py`](tools/claude_usage.py) reads the conversation files that Claude Code keeps on the computer that built this, takes **only numbers** from them (token counts, Claude Code's own cost estimate, timestamps, lines changed) and never copies any prompt or reply text. The numbers are saved in [`docs/claude-usage.json`](docs/claude-usage.json), so they stay even after Claude Code deletes its old conversation files.

<!-- usage:start -->
_Snapshot taken 11 October 2026. Cost is Claude Code's own running estimate, not a bill; days are UTC; only work on the computer that built this is counted._

| Measure | Value |
|---|---|
| Sessions | 1 |
| Days with activity | 3 (2026-10-09 to 2026-10-11) |
| Messages typed by a person (approximate) | 56 |
| Estimated cost | $62.08 |
| Time Claude spent working (API) | 1.3 hours |
| Lines added / removed in files | 9,693 / 527 |
| Tokens read fresh / written | 321,109 / 583,064 |
| Tokens read from cache / written to cache | 206,073,892 / 3,815,557 |

| Model | Cost | Fresh in | Out | Cache read | Cache write |
|---|---|---|---|---|---|
| `claude-haiku-5-5` | $0.04 | 297,513 | 15,855 | 0 | 0 |
| `claude-sonnet-5-5` | $62.04 | 23,596 | 567,209 | 206,073,892 | 3,815,557 |

| Day (UTC) | Replies | Fresh in | Out | Cache read | Cache write |
|---|---|---|---|---|---|
| 2026-10-09 | 148 | 300 | 120,649 | 44,746,399 | 1,461,243 |
| 2026-10-10 | 284 | 568 | 409,201 | 138,412,048 | 1,509,966 |
| 2026-10-11 | 126 | 252 | 75,770 | 42,326,300 | 1,578,066 |

_The per-day table counts the replies stored in the conversation file. Calls to the small helper model are only in Claude Code's own totals above, so the days add up to less than the totals._
<!-- usage:end -->

What to keep in mind:

- The cost is **Claude Code's own running estimate**, not a bill, and it depends on the plan used.
- It only sees the computer that built this. Work done anywhere else is not counted.
- "Messages typed by a person" is a count of conversation entries that look like typed messages, so treat it as approximate.
- It was added at the end, on 11 October 2026, from the conversation files that were still on disk. If an earlier session's file had been deleted before then, that session is missing.
- It is a measure of use, not of quality or of how much of the code came from where.

To refresh the numbers (this updates the table above and the saved file):

```bash
python tools/claude_usage.py --snapshot docs/claude-usage.json --update-readme README.md
```

## What it does

- **Choose what to fetch:** `pull` first lists a model's files grouped by type (safetensors, gguf, onnx, and so on) with sizes, and downloads nothing until you pick types with `--type`. Settings files, the README and the licence are always kept.
- **Fast, restartable downloads:** uses Hugging Face's own library with several connections at once. Stop it at any moment and run it again; verified files are not fetched again. Rate limits and network errors are retried with waits of 1, 2, 4, 8 and 16 seconds.
- **Everything the model page needs:** README (with a second copy whose outside pictures are stored locally, up to 7 MB each), summary details, file list with checksums and safety-scan results, history, and branches and tags, kept as Hugging Face returned them with the capture time.
- **Split to fit your drives:** `bundle` cuts a model into plain pieces of a size you set (below 1 GB if needed), or fills drives one at a time with `--interactive`. A damaged piece is replaced alone; no other piece is copied again.
- **Signed and checked:** each bundle has a description file and a signature; `verify` names every missing or damaged piece, not just the first.
- **Rebuilt for a web app:** `unpack` puts the model into a fixed folder layout (the model store) with plain-text `latest` and `refs/<name>` pointer files, no links, so it works on Linux and Windows.
- **Lists what you have:** `list` shows name, commit, capture date, size and licence for every model in a store.
- **Browse it like the Hub:** the web app in [`web/`](web/) reads the model store and offers the same pages as huggingface.co/models, with nothing fetched from the internet:
  - **Models list** (`/models`): filter by task, library, licence, language and number of parameters (the Hub's six slider stops); filter by name; sort by downloads, likes, last update, creation date or name; 30 per page. Every control is a plain link or form, so it works without JavaScript.
  - **Model card** (`/org/name`): the README rendered safely, task, library, language and licence tags, parameter counts per type, datasets and papers named in the tags, and a box saying which commit this is and when it was pulled.
  - **Files and versions** (`/org/name/tree/<rev>`): folders and files with the last commit that touched each, the Hub's safety-scan badge, a "not in store" mark on files that were listed but not downloaded; a viewer for text files and images, SHA-256s, pickle imports the Hub detected, and downloads.
  - **Commit history** (`/org/name/commits/<rev>`) and a revision menu for branches, tags and every captured commit.
  - Dark and light themes, a small JSON API (`/api/models`), and new models show up on the next page load with no restart. What it leaves out is listed in [`web/README.md`](web/README.md#what-it-does-not-do).
- **Progress and records:** live progress for anything over 2 seconds; a run record of what was fetched, skipped and failed; exit status 0, 1 (an item failed) or 2 (could not run).
- **Delivered three ways:** a single program file per system (Linux, Windows, Mac with Apple Silicon; no Python needed), an offline install pack for computers with Python, or `pip install`.

## Architecture

Two separate Python packages. The tool is `src/modelhub/`, a small command layer over single-purpose modules:

| Module | Role | Talks to |
|---|---|---|
| `cli.py` | The commands: `pull`, `bundle`, `verify`, `unpack`, `list`, `key` | the modules below |
| `hubclient.py`, `download.py`, `pull.py` | Hugging Face access, multi-connection downloads, retries, the download record | Hugging Face (online side only) |
| `filetypes.py`, `record.py`, `summary.py`, `readme_assets.py` | File grouping, record layout, model-page details, README pictures | the download record |
| `bundle.py`, `pieces.py` | Cutting a record into pieces, sizing, drive-by-drive mode | the download record, signing keys |
| `signing.py`, `verify.py`, `unpack.py`, `store.py` | Keys and trust, checks, safe rebuild, the model store and `list` | the pieces, the model store |
| `fsutil.py`, `progress.py`, `runrecord.py`, `logsetup.py`, `redact.py` | Safe file writes, locking, progress, run records, logs, hiding secrets | local disk |

The web app is `web/src/hubsite/`, with its own `pyproject.toml` and dependencies so the single-file program of the tool stays small. It never imports `modelhub`; it reads only the model-store folder layout:

| Module | Role | Talks to |
|---|---|---|
| `app.py` | Routes, security headers, file serving, JSON API | the modules below |
| `store.py` | Reads the store layout and `summary.json`, resolves revisions, lists files, refuses paths outside `files/` | the store on disk |
| `catalog.py`, `fmt.py` | Filter, sort, facet counts and paging; numbers, sizes and times written the way the Hub writes them | `store.py` |
| `markdown.py` | README to safe HTML | the store's `readme/` folder |
| `templates/`, `static/` | The pages, one stylesheet, a small optional script | none |

Only the `pull` step uses the network. The three formats between the steps are fixed contracts, written in [`contract-summary.md`](aidlc/spaces/default/intents/261009-hf-airgap-cli/inception/contract-design/contract-summary.md): the download record, the bundle, and the model store. Full design rationale and decision history: [`aidlc/`](aidlc/). The web app only reads the third contract; where each Hub field comes from in a store is in [`docs/reverse-engineering/`](docs/reverse-engineering/README.md).

## Prerequisites

- **Online computer:** Python 3.10 or newer (or the program file), internet access to Hugging Face, and disk space for the model plus the pieces.
- **Air-gapped computer:** the program file for your system, or Python 3.10+ with the offline install pack. No internet is needed or used.
- **Both sides:** a way to carry the pieces (removable drives) and a separate way to send one short fingerprint (phone, chat, paper) so the air-gapped side can trust your signing key.
- Linux or Windows, 64-bit Intel/AMD, or a Mac with Apple Silicon (macOS 11 or newer). Intel Macs can run the code with Python, but no program file is published for them.
- **Web app (optional):** Python 3.10+ and a browser, on the computer that holds the model store. Its six packages are installed with `pip`; on an air-gapped computer bring their wheels in with the offline pack route. The web app is not part of the program file.

## Quick Start

### 1. Install

```bash
pip install .            # needs Python 3.10 or newer
modelhub --version
```

Where Python is not available, use the single program file for your system (`modelhub-linux-x86_64`, `modelhub-windows-x86_64.exe`, `modelhub-darwin-arm64` for a Mac with Apple Silicon) from the GitHub release. Where Python 3.10+ is available but there is no internet, use the offline pack for your system and Python version (`modelhub-pack-<Linux|Windows>-py<3.10|3.12>.zip` from the release), unzipped:

```bash
pip install --no-index --find-links <unzipped-folder> modelhub
```

**Linux and Mac program files:** the download does not keep the "may be run" setting, so make the file runnable first: `chmod +x modelhub-linux-x86_64` (or `modelhub-darwin-arm64`).

**Mac program file:** the file is not signed with an Apple developer certificate (that needs a paid Apple account). If it was downloaded with a web browser, macOS marks it as from the internet and kills it with no message when started. Remove the mark once, then it runs:

```bash
xattr -d com.apple.quarantine modelhub-darwin-arm64
./modelhub-darwin-arm64 --version
```

Files copied on a USB drive from a computer that did not download them normally carry no such mark.

### 2. Once: make a signing key (online side) and trust it (air-gapped side)

```bash
modelhub key create                          # prints the key id and fingerprint
modelhub key export <key-id> --out modelhub-public.key
```

From version 1.1.1, anywhere a command asks for a key you can give its key id, its fingerprint (with or without dashes, any capitals) or the first few characters of either. Version 1.1.0 and earlier accept only the exact key id. `modelhub key list` shows them.

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

### 6. Browse the store (air-gapped, optional)

```bash
cd web
python3 -m venv .venv && source .venv/bin/activate
pip install -e .                                     # FastAPI, uvicorn, Jinja2, markdown-it-py, mdit-py-plugins, nh3
python -m hubsite --store /srv/models --port 8765    # then open http://127.0.0.1:8765
```

Search from the header, filter on the left, open a model, then try **Files and versions** and the revision menu. The site only reads the store; it never changes it. `web/README.md` has the page list and details. A store built from four small public models is in `store/` after the steps above are run on those models (it is not committed: it is about 100 MB).

### Recovering by hand

Pieces are plain slices of one tar file; the signature file lists their names and checksums.

```bash
cat name.part-000001 name.part-000002 > name.tar          # Linux
```
```
copy /b name.part-000001+name.part-000002 name.tar        (Windows)
```

## Stopping / Resetting

Stop any command with Ctrl-C at any moment and run it again; it continues from the verified work. Only one run may use an output folder at a time. To start over, delete the output folder (`pulled`, the pieces folder, or the store). Stop the web app with Ctrl-C; it keeps no data of its own, and only your light or dark choice is remembered, in your browser.

## Configuration Reference

There is no config file. The few settings:

- **`HF_TOKEN`** — optional Hugging Face token (or `--ask-token` for a hidden prompt). Never accepted on the command line.
- **`MODELHUB_HOME`** — where signing keys and trusted keys are kept (default `~/.modelhub`). Use two different folders to try both sides on one computer.
- **`--workers`** — files downloaded at once (default 8).
- **`--piece-size`** — largest piece, for example `900MB`; the smallest accepted is documented in the code and is far below 1 GB.
- **`--verbose` / `--debug`** — also write `modelhub.log` beside the output.
- `HF_HUB_DISABLE_TELEMETRY` and the update check are switched off by default.

The web app has no config file either: `--store` (or `HUBSITE_STORE`, default `./store`), `--host` (default `127.0.0.1`, this computer only; use `0.0.0.0` only on a network you trust, since there is no login) and `--port` (default 8000).

## Development

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                       # real-network tests are skipped; run them with: pytest -m network
ruff check . && ruff format --check .
python tools/benchmark_download.py org/model big-file.bin   # speed check against the link (80%)
```

### The web app

```bash
cd web && python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                                  # 24 tests; no internet and no real store needed
ruff check . && ruff format --check .   # web/ has its own ruff settings (line length 140)
```

The tests build a tiny store in a temporary folder. To look at the site while changing it, run it with `--store ../store` and reload. The root `pytest` and `ruff` commands do not run the web tests; CI has a separate `web` job for them.

### Build the program file

```bash
pip install -e ".[build]"
python packaging/build.py pyinstaller
python packaging/roundtrip_smoke.py dist/modelhub-<system>-x86_64   # runs the whole workflow
python packaging/offline_pack.py                                    # the offline install pack
```

The checks in `.github/workflows/ci.yml` do this on every pull request; pushing a tag such as `v1.1.1` runs them and then attaches the files to a GitHub release.

Full instructions: [`aidlc/spaces/default/intents/261009-hf-airgap-cli/construction/build-and-test/`](aidlc/spaces/default/intents/261009-hf-airgap-cli/construction/build-and-test/).

## Troubleshooting

**`verify` or `unpack` refuses the bundle because its key is not trusted** — this computer has not trusted the key. Run `modelhub key trust` with the public key file and type the fingerprint you received separately.

**`verify` names a missing or damaged piece** — copy just that piece again from the source and run `verify` again; no other piece needs copying.

**`pull` says a model is not found, or is private or gated** — the Hub reports the same answer for all three; only public models are supported.

**"another run is using <folder>"** — a second `modelhub` is running on the same output folder, or an earlier one is still open. Close it, or wait. A run that was killed releases the folder by itself.

**The Mac program file is killed as soon as it starts (exit status 137)** — macOS has marked it as downloaded from the internet. Run `xattr -d com.apple.quarantine <file>` once.

**Web app says "No models in this store yet"** — `--store` must be the folder that contains `models/`, not `models/` itself. `modelhub list <store>` shows what it holds.

**A model is missing from the web list** — it is skipped if it has no `commits/<commit>/summary.json` or that file is damaged. `modelhub verify <store>` checks every file.

**A file shows "not in store"; a picture in a model card shows as `[name]`** — the first was listed by the Hub but not downloaded (pull again with a `--type` that includes it); the second pointed to the internet and could not be copied. The site never loads remote pictures.

**The program file will not start on an old Linux** — it must be built on RHEL 8 or older; the CI does this, a build on a newer system will not run there.

## Project Structure

```
src/modelhub/          The tool: commands and modules (see Architecture)
web/                   The web app (own pyproject.toml): src/hubsite/, tests/ (24), README.md
docs/                  claude-usage.json (saved usage numbers); reverse-engineering/ (screenshots and notes from studying huggingface.co/models with REA)
store/                 Optional sample model store for the web app (git-ignored)
tests/                 369 tests (+6 against the real Hub; 6 skipped on Windows); conftest.py holds a fake Hugging Face
packaging/             Program-file build, offline install pack, whole-workflow smoke script
tools/                 benchmark_download.py (manual speed check), claude_usage.py (Claude Code usage tracker)
.github/workflows/     ci.yml (checks and builds) and release.yml (publish on a v* tag)
aidlc/                 Design docs, requirements, decision history, audit trail
pyproject.toml         Dependencies, version, ruff and pytest settings
```
