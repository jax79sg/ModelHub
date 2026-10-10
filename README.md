# modelhub

Download public Hugging Face models (files, README, metadata) on a computer with internet, carry
them on removable drives as signed pieces into an air-gapped environment, and rebuild them there
into a folder layout that a web app can read directly. Runs on Linux and Windows on both sides.

```
online computer                              drives                 air-gapped computer
pull  ->  bundle (signed, split)  ->  carry  ->  verify  ->  unpack  ->  list
```

## Install

```bash
pip install .            # needs Python 3.10 or newer
modelhub --version
```

Where Python is not available, use the single program file for your system
(`modelhub-linux-x86_64`, `modelhub-windows-x86_64.exe`), downloaded from the GitHub release.
Where Python 3.10+ is available but there is no internet, use the offline pack for your system and
Python version (`modelhub-pack-<system>-py<version>.zip` from the release), unzipped:

```bash
pip install --no-index --find-links <unzipped-folder> modelhub
```

## Workflow

### 1. Once: make a signing key (online side) and trust it (air-gapped side)

```bash
modelhub key create                          # prints the key id and fingerprint
modelhub key export <key-id> --out modelhub-public.key
```

Carry `modelhub-public.key` to the air-gapped side. Send its **fingerprint by a different route**
(phone, chat, paper). On the air-gapped computer:

```bash
modelhub key trust modelhub-public.key       # asks you to type the fingerprint
modelhub key list
```

A bundle signed by a key that is not trusted is refused.

### 2. Download (online)

```bash
modelhub pull org/name                       # shows the file types found; downloads nothing yet
modelhub pull org/name --type safetensors --type json
modelhub pull --list models.txt --type all   # one model id per line, # for comments
```

Large files use several connections. A stopped run is simply started again and carries on. A token
for gated models comes from `HF_TOKEN` or `--ask-token`; it is never written to a log or record.
Each model lands in `pulled/models/<id>/commits/<commit>/`.

### 3. Pack for the drives (online)

```bash
modelhub bundle pulled/models/org/name/commits/<commit> --out outgoing --piece-size 900MB
modelhub bundle <record> --out outgoing --interactive    # fill drives one at a time
```

This writes plain pieces plus a `.bundle.json` and a `.bundle.sig` signature file. Copy the whole
folder (or spread the pieces across drives, keeping the two small files with the first).

### 4. Check and rebuild (air-gapped)

```bash
modelhub verify /media/drive1 /media/drive2          # signature and every piece
modelhub unpack /media/drive1 /media/drive2 --store /srv/models
modelhub list /srv/models
modelhub verify /srv/models                          # re-check every file of the store later
```

The store holds `models/<id>/commits/<commit>/{files,raw,readme,manifest.json,summary.json}` plus
`latest` and `refs/<name>` text files naming a commit. These are plain files, not links.

Exit status: `0` all fine, `1` something failed (named on screen), `2` the command could not run.

### Recovering by hand

Pieces are plain slices of one tar file; the signature file lists their names and checksums.

```bash
cat name.part-000001 name.part-000002 > name.tar          # Linux
```
```
copy /b name.part-000001+name.part-000002 name.tar        (Windows)
```

## Build the program file

```bash
pip install -e ".[build]"
python packaging/build.py pyinstaller
python packaging/roundtrip_smoke.py dist/modelhub-<system>-x86_64   # runs the whole workflow
python packaging/offline_pack.py                                    # the offline install pack
```

The checks in `.github/workflows/ci.yml` do this on every pull request; pushing a tag such as
`v1.0.0` runs them and then attaches the files to a GitHub release.

## Development

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                       # real-network tests are skipped; run them with: pytest -m network
ruff check . && ruff format --check .
python tools/benchmark_download.py org/model big-file.bin   # speed check against the link (80%)
```
