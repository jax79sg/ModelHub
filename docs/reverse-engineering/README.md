# Reverse engineering huggingface.co/models

How the pages of the web app in [`web/`](../../web/) were designed. The pages were studied with [REA](https://github.com/morluto/rea) (`rea-agents` 6.4.0): `list-browser-targets`, `inspect-web-page` and `capture-web-screenshot` against a throw-away headless Chrome with its own empty profile, on **11 October 2026**. Only public pages were opened, nothing was signed in to.

## Screenshots

| Page | Capture |
|---|---|
| Models list | [`models-list.png`](models-list.png) |
| Model card | [`gpt2.png`](gpt2.png) |
| Files and versions | [`gpt2-tree.png`](gpt2-tree.png) |
| Commit history | [`gpt2-commits.png`](gpt2-commits.png) |

The raw REA output (about 4.5 MB of DOM, accessibility tree, script list and the pages' own HTML and CSS) is not committed: it is copies of someone else's pages. Re-create it with the commands above.

## What was found

- **Stack.** Server-rendered Svelte (a "kube" build, Rolldown chunks, a Tailwind v4 palette). Each widget's data is embedded as JSON in `data-target="…" data-props="…"` and hydrated in the browser. Components seen: `ModelList`, `FilteredList`, `Pagination`, `SortingDropdown`, `ListSearchInput`, `ModelHeader`, `ModelTensorsParams`, `SideNavigation`, `ViewerIndexTreeList`, `LastCommit`, `Commit`, `RepoCodeCopy`.
- **List data.** `ModelList.initialValues` has `activeFilters` (`pipeline_tag`, `num_parameters`, `library`, `apps`, `inference_provider`, `hardware`, `language`, `license`, `other`, …), `displayedFilter` (the Main / Tasks / Libraries / Languages / Licenses / Other tabs), `numItemsPerPage` (30), `pageIndex`, `searchQuery`, `sortBy`, and one object per model (`id`, `downloads`, `likes`, `lastModified`, `pipeline_tag`, `numParameters`, `authorData`).
- **Links.** The page links confirm the query model the web app copies: `?p=<n>&sort=trending`, `?pipeline_tag=…`, `?library=…`.
- **Parameter slider.** Six stops: < 1B, 6B, 12B, 32B, 128B, > 500B.
- **Model page data.** `ModelHeader` carries `cardData` (license, language, tags), `tag_objs` (typed tags: pipeline_tag, library, language, license, dataset, arxiv), `safetensors` (per-type parameter counts), `createdAt`, `lastModified`, `downloads`, `likes`.

## Where each field comes from in a model store

| What the Hub page shows | Where the web app reads it |
|---|---|
| task, library, tags, license, language | `summary.json` → `card.*` |
| downloads, likes, parameter counts per type | `summary.json` → `stats.*` |
| created / last modified | `summary.json` → `created_at`, `last_modified` |
| files tree with last commit per file | `raw/tree.json`, plus `summary.json` → `files[]` for what was really downloaded |
| commits, branches and tags | `raw/commits.json`, `raw/refs.json`, `refs/<name>` |
| safety scan and pickle imports | `summary.json` → `files[].scan` |
| README and its pictures | `readme/README.local.md` and `readme/assets/` |

## Not reproduced

A model store has nothing to build these from: the Trending sort, inference widgets and providers, Spaces, the model tree of adapters and finetunes, community discussions, sign-in, likes and follows, the Datasets and Spaces tabs, the download-history chart and author avatars.
