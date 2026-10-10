# Contract Summary

Inputs: `requirements.md` (from `inception/requirements-analysis/`) and your answers in `contract-design-questions.md` (Q1 to Q6). The plan skipped the step that splits work into units, so no `unit-of-work` or `unit-of-work-dependency` documents exist: the system is one tool with two halves, and the contracts below are the agreements across its boundaries. IDs such as FR6.5 and NFR2 refer to `requirements.md`.

## Contracts

| # | Provider | Consumer | Mechanism | Owner |
|---|----------|----------|-----------|-------|
| C1 | `pull` (download side) | `bundle` (download side), with a scan by other people in between | A folder of files on disk: the download record | You |
| C2 | `bundle` (download side) | `verify` and `unpack` (air-gapped side) | Pieces plus a manifest, carried on drives | You |
| C3 | `unpack` (air-gapped side) | External: the air-gapped web app, built later | Files in a folder; no server (Q1 A) | You |
| C4 | The command-line program | External: the person running it, and any scripts | Commands, options, exit status | You |

## C1: The Download Record

Written by `pull`, one folder per model per exact version (commit). The scan (Q5 C) is done on the files in this folder before any piece is made. `bundle` must prove that what it packs is what was scanned.

```yaml shared-schema
contract: C1-download-record
format_version: "1.0"
location: "<work>/models/<model_id>/commits/<commit_id>/"
model_id: "canonical Hugging Face id as returned by the Hub, for example openai-community/gpt2"
contents:
  files/: "the model files at their original relative paths, exactly as downloaded"
  raw/: "Hugging Face responses exactly as returned: model_info.json, tree.json, commits.json, refs.json"
  readme/: "README.local.md (pictures pointing to local copies) and assets/ (the downloaded pictures); the original README stays in files/"
  summary.json: "the stable summary (see C3)"
  manifest.json: "download-time manifest"
manifest.json:
  format_version: "string, major.minor"
  tool_version: "string"
  captured_at: "ISO 8601 UTC time"
  model_id: "string"
  commit: "full commit identifier"
  files:
    - path: "relative path, forward slashes"
      size: "integer bytes"
      sha256: "lowercase hex"
      hub_sha256: "lowercase hex or null; the checksum Hugging Face reported, null when none is reported"
      scan: "object copied from Hugging Face's per-file safety results, or null"
rules:
  - "bundle recomputes every file's sha256 and refuses to continue if any differs from manifest.json; the scanned content is then provably the packed content (FR6.1, FR5.4)"
  - "A file that failed its Hub checksum check is never listed as complete (FR5.4)"
  - "Writes go to a temporary name and are renamed when complete, so a stopped run never leaves a half-written file that looks finished (FR6.6, NFR3)"
```

## C2: The Bundle

Made by `bundle`, read by `verify` and `unpack` inside the air-gapped environment. The pieces are plain, uncompressed slices (Q6 A): the commit folder from C1 is written as one standard uncompressed archive (POSIX "pax" tar), and that single stream is cut into consecutive slices. Putting the slices back in order, with standard operating-system tools, gives back the archive, and any standard archive tool can open it. A single model file is never compressed, because model weights rarely shrink.

```yaml shared-schema
contract: C2-bundle
format_version: "1.0"
piece_naming: "<model_id with / replaced by -->--<commit first 12 chars>.part-<index of 6 digits>-of-<count of 6 digits>"
manifest_file: "<same stem>.bundle.json, kept beside the pieces on the first drive and written again on the last"
stream:
  archive: "POSIX pax tar, uncompressed"
  root: "the C1 commit folder"
  sha256: "checksum of the whole joined stream"
  size: "integer bytes"
pieces:
  - index: "integer, starting at 1"
    name: "string"
    size: "integer bytes, at most piece_size_max"
    sha256: "lowercase hex; the checksum of this piece alone"
    offset: "integer bytes from the start of the stream"
fields:
  piece_size_max: "integer bytes chosen by the user (FR6.2) or drive size given interactively (FR6.3)"
  created_at: "ISO 8601 UTC"
  tool_version: "string"
  model: {id: "string", commit: "string", captured_at: "ISO 8601 UTC"}
  c1_manifest_sha256: "checksum of the C1 manifest.json, tying the bundle to what was scanned"
rules:
  - "Every piece can be checked alone from its own sha256 and name (FR6.5, NFR4)"
  - "Pieces can arrive from several drives in any order; the index and count say what is missing (FR7.5)"
  - "By hand, with no tool: join the pieces in index order (Linux: cat <stem>.part-* > <stem>.tar; Windows: copy /b ... <stem>.tar), then extract with a standard archive tool"
  - "Smallest allowed piece_size_max is documented and below 1 GB (FR6.4)"
  - "The bundle stage refuses to start without enough free space for the pieces (FR6.7)"
```

## C3: The Rebuilt Model Folder (read by the web app)

Left by `unpack`, read directly from disk by the web app (Q1 A). This tool never runs as a server. Several versions of a model sit side by side, with a marker for the latest (Q4 A). Markers are small text files, not links, because links are unreliable on Windows without special rights (`constraint-register.md` CT-7).

```yaml shared-schema
contract: C3-model-store
format_version: "1.0"
layout:
  "<store>/models/<model_id>/latest": "text file holding the commit identifier of the most recently captured default-branch version"
  "<store>/models/<model_id>/refs/<ref_name>": "text file holding a commit identifier, one per branch or tag (nested folders for names with /)"
  "<store>/models/<model_id>/commits/<commit_id>/": "the C1 commit folder, rebuilt and checked"
the_web_app_reads: "summary.json first; it names every other file it points to"
summary.json:
  format_version: "string, major.minor"
  tool_version: "string"
  model_id: "string"
  commit: "string"
  captured_at: "ISO 8601 UTC; every count below is a snapshot at this time"
  card:
    license: "string or null"
    language: "list of strings or null"
    tags: "list of strings"
    pipeline_tag: "string or null"
    library_name: "string or null"
  stats:
    downloads: "integer or null"
    likes: "integer or null"
    used_storage_bytes: "integer or null"
    parameter_counts: "object or null"
  created_at: "ISO 8601 or null"
  last_modified: "ISO 8601 or null"
  license:
    name: "string or null"
    file: "relative path of a licence file in files/, or null"
    text_available: "boolean"
  readme:
    original: "files/README.md or null"
    local: "readme/README.local.md or null"
    pictures:
      - source: "original address"
        local: "relative path or null"
        status: "fetched | failed | skipped"
  files:
    - path: "relative path"
      size: "integer bytes"
      sha256: "lowercase hex"
      type: "file type group used in the type listing, for example safetensors"
      scan: "object or null"
  history:
    commits_file: "raw/commits.json"
    refs_file: "raw/refs.json"
rules:
  - "A field Hugging Face did not give is null, never 0 or an empty string; 'unknown' and 'zero' stay distinct (corner checklist: numbers and units)"
  - "Additive change only within a major version: the web app ignores fields it does not know (ownership rules below)"
  - "A rebuilt file that fails its manifest checksum is not left in this folder (FR7.3)"
  - "raw/ holds Hugging Face's responses exactly as returned; the web app may read them but is not promised their shape (Q2 C)"
  - "The web app must work from summary.json alone for everything it shows except the README, pictures and the model files"
```

## C4: The Command Line

The surface for the person running the tool. Command names follow the existing prototype and may be renamed in a later step, with the same behaviour.

```yaml cli
contract: C4-command-line
commands:
  pull: "download one model or a list of models into C1 folders (FR1, FR2, FR3, FR4, FR5)"
  bundle: "check a C1 folder against its manifest, then write pieces and a manifest (FR6)"
  verify: "check pieces or a model store against their manifests, naming anything missing or damaged (FR7.1, FR7.5)"
  unpack: "rebuild pieces into a C3 model store (FR7.2, FR7.3)"
  list: "list models in a store with name, commit, capture date, size and licence name (FR7.4)"
  "--version": "print the tool version (FR8.3)"
exit_status:
  0: "everything asked for completed"
  1: "at least one item failed; the others were still processed, and the run record names each failure (FR1.4, FR9.1)"
  2: "the command could not run: wrong options, missing input, not enough free space"
output:
  human_readable: "progress and errors on the screen; errors name the file or step and the reason (FR9.1)"
  run_record: "run-record.json written beside the output, listing fetched, skipped and failed items (FR9.2)"
rules:
  - "pull with no file-type selection prints the types found and stops with status 0 and downloads nothing (FR2.3)"
  - "An access token is never written to any file or message (NFR6)"
  - "unpack, verify and list make no network connection (FR7.6, NFR5)"
```

## Ownership And Change Rules

- You own all four contracts. One person owns both sides, so a change is agreed by you alone, but it is still recorded here before it is built.
- Every file in C1, C2 and C3 carries `format_version` as `major.minor` (Q3 A).
- A newer tool must always read bundles and stores made by an older tool with the same or an earlier major version. A change that stops older ones being read raises the major version, and the old reading rules stay in the tool.
- Additive changes (a new optional field or file) raise only the minor version. Readers, including the web app, ignore fields they do not know.
- The web app reads only what is named in C3; it must not rely on file ordering or on anything in `raw/`.

## Open Questions

| Contract | Question | Blocks |
|----------|----------|--------|
| C2 | Does the standard archive named here (POSIX pax tar) open with the tools already present on the air-gapped Windows and Linux computers, including for files over 8 GB? | Code generation of `bundle` and `unpack` |
| C3 | Hugging Face model names are case-insensitive in some places and Windows folders are too: how are two ids differing only in case handled? | Folder naming in `unpack` |
| C1 and C2 | Is an explicit "scan passed" marker from the scanning people wanted, or is proving the files unchanged enough? | Whether `bundle` takes an extra input |
| C4 | Is a machine-readable output option (for example JSON on the screen) needed, or is the run record enough? | CLI tests |
| C4 | Are the final command names the existing ones (`pull`, `bundle`, `verify`, `unpack`) plus `list`? | CLI help text and tests |
