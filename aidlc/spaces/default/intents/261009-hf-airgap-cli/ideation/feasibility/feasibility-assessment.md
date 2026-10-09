# Feasibility Assessment

Inputs: `intent-statement` (from `ideation/intent-capture/`), your answers in `feasibility-questions.md`, and research done on 2026-10-09 against Hugging Face's official documentation and its public service. Companion documents: `constraint-register.md` and `raid-log.md`.

## Verdict

**Feasible, with three conditions to settle early.** The conclusion is deliberately cautious: the research tested one or two sample models, not a broad range.

- Everything the request asks for in terms of *getting data out of Hugging Face* can be done with Hugging Face's own official libraries and command-line tool, with no web scraping (see "What can be retrieved").
- Faster downloads of big files are supported by the official route, and the file server supports the technique that multi-connection downloads rely on (see "Faster downloads").
- Conditions to settle:
  1. **How the tool gets installed and run inside the air-gapped environment** on both Linux and Windows, where nothing can be fetched from the internet (answer to Q3).
  2. **Splitting into very small pieces.** The smallest transfer drive is under 1 GB (Q9) while some models are over 100 GB (Q5), so a single model may need hundreds of pieces.
  3. **The one-month deadline** (Q10) against everything above. The scope likely needs trimming or ordering.

| Question | Confidence | Why |
|----------|------------|-----|
| Can the data be retrieved without scraping? | High | Official endpoints and libraries returned it for a sample model (E3 to E6) |
| Can big files be fetched faster? | Medium-High | Official fast-transfer path exists (E8); range requests work on a sample file (E7); real speed on your network is unmeasured |
| Can it run on Linux and Windows? | Medium-High | The official library and its fast-transfer component ship for both (E8); installing inside the air-gapped side is unproven |
| Can it be done within about one month? | Medium | Depends on the scope chosen in later steps |

## What Can Be Retrieved

All of this was returned **without logging in** for a public sample model (`openai-community/gpt2`) on 2026-10-09 (E3 to E6), apart from items marked otherwise.

| Information | How it is obtained | Notes |
|-------------|--------------------|-------|
| Model card text (README) and its settings header (licence, language, tags) | The file itself, downloaded like any other file | Available (E5) |
| Summary details: author, tags, task type, licence, library, created and last-changed dates, download and like counts, size on disk, parameter counts, example-widget settings | Model information endpoint | Counts are a snapshot at download time (E3) |
| Full file list with sizes and checksums | File-tree endpoint | Each large file carries its SHA-256 checksum (E4) |
| Hugging Face's own safety-scan results per file (virus, malware, pickle checks) | Same file-tree endpoint | Third-party results as of download time; useful input for your approval step (E4) |
| Change history (commits) and named versions (branches, tags) | Commits and refs endpoints | Available (E6) |
| Community discussions | Discussions endpoint | Available; 183 threads for the sample model (E6) |
| Evaluation results, base-model links, quantization details, inference-provider settings | Extra fields in the official library's model-information call | Listed in the library's documentation of requestable fields (E3) |
| The model files themselves | Official download functions and the `hf download` command | Filters by file pattern and a "dry run" that prints total size first (E11) |

## What Cannot Be Brought Across As-Is

These are limits of the idea, not of the tool. They affect the success measure "same key information as huggingface.co" (see `intent-statement`).

- **Live parts of the page**: running example widgets and live inference need Hugging Face's servers. Only their settings can be carried (hypothesis: the web app can show a "not available offline" note instead).
- **Images and links hosted elsewhere**: a sample README (`Qwen/Qwen2.5-7B-Instruct`) loads a badge from an outside site (E5). These break offline unless fetched and rewritten.
- **Avatars and other site assets**: discussions refer to avatar images by site path (E6); they are not part of the repository.
- **Counts that change**: downloads and likes are frozen at the moment of download.
- **Spaces, datasets and collections linked from a model**: only their names appear (E3). Their content is outside the first version (see `intent-statement`, Q8).

## Faster Downloads

- **Official fast path**: the Python library installs a companion component (`hf_xet`) that downloads large files in many parallel pieces. A setting named `HF_XET_HIGH_PERFORMANCE` tells it to use all CPU cores and try to use the full network bandwidth (E8).
- **Older route retired**: the earlier fast-transfer add-on (`hf_transfer`) is documented as deprecated and can no longer be used (E8). Anything built on it would break.
- **Several files at once**: whole-model downloads already fetch several files concurrently; the command-line tool's default is 8 (E11).
- **Underlying technique works**: the file server answered a partial-file request correctly (HTTP 206, `Accept-Ranges: bytes`) from its content-delivery host (E7). This is the property that lets a file be fetched in parallel pieces.
- **Not yet known**: how much faster this is on your network. A rough calculation only: at 1 Gbit/s a 100 GB model needs about 13 minutes at best, and at 100 Mbit/s about 2 hours 10 minutes (calculation, not measured). Your actual bandwidth was not asked and is an open item in `raid-log.md`.

## Language Options (Viability Only)

No language is chosen here. This records which are viable, so later steps can decide.

| Option | Official Hugging Face support | Fit with your answers | Open issue |
|--------|-------------------------------|-----------------------|------------|
| Python | Official library and command-line tool, including the fast-transfer component; needs Python 3.10 or newer (E1, E8) | You are comfortable with it (Q7); a prototype in this project already uses it | Installing inside the air-gapped side on both operating systems (hypothesis: a self-contained executable or an offline package set could solve it; **not tested**) |
| JavaScript / TypeScript | Official library with file listing, model information and whole-repository download (E12) | Not among your skills (Q7) | Fast-transfer support not confirmed from the documentation read |
| Rust | Library from the Hugging Face organisation; its README lists fast-transfer support (E12) | Not among your skills (Q7) | Windows and Linux support not stated in what was read |
| Go | No official library found in the documentation reviewed (not verified) | Not among your skills (Q7) | Would mean calling raw web endpoints |

On present evidence only Python is both fully supported by official tooling and within your stated skills. It stays a candidate, not a decision.

## Linux and Windows Notes

- The fast-transfer component is published for Linux (x86-64 and ARM, two C-library flavours), Windows (x86-64 and ARM) and macOS (E8).
- On Windows, the default download cache needs symlinks, which require Developer Mode or administrator rights. Without them it still works but stores duplicate copies, using more disk (E10). Downloading straight to a chosen folder avoids the cache layout.
- Hugging Face's cache layout can be copied as folders and used offline with `HF_HUB_OFFLINE=1`; a partly copied snapshot is reported as incomplete rather than silently accepted (E13).

## Limits Imposed by Hugging Face

- Without logging in, each internet address may make about 500 information requests and 3,000 file requests per 5 minutes; a free account about 1,000 and 5,000 (E9). A live response showed the same figure (`q=500`, 300-second window).
- Hugging Face recommends always sending an access token. The official library (1.2.0 or newer) waits and retries when it is told to slow down (E9).
- Gated and private models need a token and acceptance of terms; they are outside the first version (see `intent-statement`).

## Traceability To The Intent

| Point in `intent-statement` | Feasibility finding |
|-----------------------------|---------------------|
| Download README text and other metadata for public models | Feasible, official endpoints, no scraping (E3 to E6) |
| Model page in the web app shows the same key information as huggingface.co | Partly: live widgets, outside images and avatars are not carried (see above). The list of "key information" still has to be defined (R8 in `raid-log.md`) |
| Large files download noticeably faster | Feasible via the official fast path; size of the gain unmeasured (A1 in `raid-log.md`) |
| Easy install and use on Linux and Windows | Download side: feasible. Air-gapped side: unproven (R3 in `raid-log.md`) |
| Out of first version: private or gated models, datasets and Spaces, the web app itself | Consistent with the findings |

## Evidence

Checked on 2026-10-09. "Sample" means one or two models, so results are indicative only.

- E1: Official Python library and `hf` command-line tool; Python 3.10 or newer for the installed version (2.2.0). https://huggingface.co/docs/huggingface_hub/guides/cli ; package index entry for `huggingface-hub`.
- E2: Open Hub endpoints, described in a machine-readable specification at https://huggingface.co/.well-known/openapi.json ; the Python and JavaScript clients wrap them. https://huggingface.co/docs/hub/api
- E3: Sample call to the model information endpoint for `openai-community/gpt2`, no login: returned author, card data, config, dates, downloads, likes, safetensors summary, file list, linked spaces, tags, widget data. Extra fields available through the library's `expand` option are listed in its `model_info` documentation (installed version 2.2.0).
- E4: Sample file-tree call: each file has size, SHA-256 (`lfs.oid`), a storage hash (`xetHash`) and per-scanner safety results (`securityFileStatus`).
- E5: Sample README download (`gpt2`, `Qwen/Qwen2.5-7B-Instruct`): text with a settings header; one sample loads an image badge from another website.
- E6: Sample commits (26), refs (tags, branches), and discussions (count 183, with avatar paths) for `gpt2`.
- E7: Sample partial-file request on `gpt2/64-8bits.tflite`: HTTP 206, `Content-Range: bytes 0-1023/125162496`, served from `us.aws.cdn.hf.co`.
- E8: Faster downloads and the retired older add-on: https://huggingface.co/docs/huggingface_hub/guides/download ; https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables . Platform builds from the `hf-xet` package index entry (version 1.7.0).
- E9: Rate limits (September 2025 figures): https://huggingface.co/docs/hub/rate-limits ; header seen in a live response: `"api";r=499;t=155`, policy `q=500;w=300`.
- E10: Cache and Windows symlink limitation: https://huggingface.co/docs/huggingface_hub/guides/manage-cache
- E11: `hf download` options (`--include`, `--exclude`, `--local-dir`, `--revision`, `--max-workers`, `--dry-run`) and metadata commands (`hf models info`, `hf models card --metadata --format json`): https://huggingface.co/docs/huggingface_hub/package_reference/cli
- E12: JavaScript library https://huggingface.co/docs/huggingface.js/hub/README ; Rust crate https://github.com/huggingface/hf-hub
- E13: Offline use and incomplete-snapshot detection: https://huggingface.co/docs/huggingface_hub/guides/manage-cache ; https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables

## Glossary

- **Air-gapped**: a network with no connection to the internet.
- **Partial-file request (range request)**: asking a server for just a slice of a file, which is how one file can be fetched in several parallel pieces.
- **Safetensors**: a model file format that stores only numbers, not runnable code.
- **Pickle**: an older model file format that can contain runnable code, which is why scanners check it.
- **Symlink**: a shortcut to another file, used by Hugging Face's local cache to avoid storing copies twice.
