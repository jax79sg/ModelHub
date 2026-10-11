# modelhub web app (`hubsite`)

A read-only, offline look-alike of the Hugging Face model pages, filled entirely from a **modelhub model store**: the folder that `modelhub unpack --store <folder>` writes. Nothing is fetched from the internet while it runs: no CDN scripts, no remote fonts, no remote avatars, no remote README pictures.

It is branded "ModelHub" on purpose. It copies how the Hub's pages are organised, not its name, logo or code.

How it was designed, checked and hardened, and what it is not, is in the [main README](../README.md#how-this-was-reviewed-and-hardened). How the pages were reverse engineered, with screenshots: [`docs/reverse-engineering/`](../docs/reverse-engineering/README.md).

## Run it

```bash
cd web
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"                      # leave out [dev] to only run it
python -m hubsite --store ../store --port 8765
```

Then open **http://127.0.0.1:8765**. Options: `--store` (or `HUBSITE_STORE`, default `./store`), `--host` (default `127.0.0.1`; there is no login, so use `0.0.0.0` only on a network you trust), `--port` (default 8000). Models unpacked into the store later appear on the next page load; no restart.

To make a store, use the CLI (see the [main README](../README.md#quick-start)): `modelhub pull`, `bundle`, `verify`, `unpack --store store`.

## Pages

| URL (same shape as the Hub) | Shows | Reads |
|---|---|---|
| `/models` | list; task, library, licence, language and parameter filters; name filter; sort; 30 per page | every `summary.json` |
| `/{org}/{name}` | model card (README), tags, parameter counts, datasets, papers, capture info | `summary.json`, `readme/README.local.md` |
| `/{org}/{name}/tree/{rev}[/dir]` | files and folders, last commit per file, scan badge, "not in store" mark | `raw/tree.json`, `summary.json`, `raw/commits.json` |
| `/{org}/{name}/blob/{rev}/{path}` | text viewer (first 512 kB), SHA-256, scan result, pickle imports, images | `files/`, `summary.json` |
| `/{org}/{name}/resolve/{rev}/{path}` · `/raw/…` | download · plain text | `files/` |
| `/{org}/{name}/commits/{rev}` | commit history | `raw/commits.json`, `raw/refs.json` |
| `/api/models`, `/api/models/{org}/{name}` | the same data as JSON | `summary.json` |

`{rev}` is a branch or tag name from `refs/`, `latest`, or any captured commit id (7 or more characters). Model ids must be `org/name`; single-word legacy ids such as `gpt2` are not routed.

## Where each Hub field comes from

| What the Hub page shows | Where it is read |
|---|---|
| task, library, tags, licence, language | `summary.json` → `card.*` |
| downloads, likes, parameter counts per type | `summary.json` → `stats.*` |
| created / last modified | `summary.json` → `created_at`, `last_modified` |
| files tree with last commit per file | `raw/tree.json`, plus `summary.json` → `files[]` for what was really downloaded |
| commits, branches and tags | `raw/commits.json`, `raw/refs.json`, `refs/<name>` |
| safety scan and pickle imports | `summary.json` → `files[].scan` |
| README and its pictures | `readme/README.local.md` and `readme/assets/` |

Odd data is tolerated: a missing README, null numbers, `license` given as a list, a `tree.json` that lists files never downloaded, and several captured commits of one model.

## What it does not do

The store has nothing to build these from, so they are left out: the Trending sort (needs live activity), inference widgets and providers, Spaces, the model tree of adapters and finetunes, community discussions, sign-in, likes and follows, the Datasets and Spaces tabs, the download-history chart and author avatars (a coloured letter is drawn instead). Downloads and likes are a snapshot from the day each model was pulled and are labelled that way.

## Layout

```
src/hubsite/
  app.py          routes, security headers, file serving, JSON API
  store.py        reads the store layout; refuses paths outside files/
  catalog.py      filter, sort, facets, paging
  markdown.py     README to safe HTML
  fmt.py          numbers, sizes and times written the way the Hub writes them
  templates/      the pages
  static/         app.css, app.js (optional), theme.js
tests/            24 tests and the fake store they build (conftest.py)
```

## Test

```bash
pytest                                   # no internet and no real store needed
ruff check . && ruff format --check .    # this folder has its own ruff settings
```

## Troubleshooting

**"No models in this store yet"** — `--store` must be the folder that contains `models/`, not `models/` itself. `modelhub list <store>` shows what it holds.

**A model is missing from the list** — it is skipped if it has no `commits/<commit>/summary.json`, or that file is damaged. `modelhub verify <store>` checks every file.

**A file shows "not in store"** — the Hub lists it but it was not downloaded. Pull the model again with a `--type` that includes it.

**A picture in a model card shows as `[name]` in a dashed box** — it was a link to the internet that `modelhub` could not copy. The site never loads remote pictures.

**Port already in use** — pick another with `--port`.
