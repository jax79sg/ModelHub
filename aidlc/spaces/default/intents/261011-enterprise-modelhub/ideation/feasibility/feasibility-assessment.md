# Feasibility Assessment

Inputs: `intent-statement` (from `ideation/intent-capture/`), your answers in `feasibility-questions.md`, and research done on 12 October 2026 in JFrog's public documentation, in the installed `huggingface_hub` 2.2.0 library, and in this project's `pyproject.toml`. Companion documents: `constraint-register.md` and `raid-log.md`.

## Verdict

**Feasible, with four conditions to settle in the next stages.** The conclusion is cautious: no real Artifactory was available (intent capture Q17, feasibility Q11), so everything about it rests on JFrog's documentation, not on a test.

- The idea fits what Artifactory documents: a Hugging Face repository takes a model uploaded under a commit hash and serves it back to standard clients (E2). Putting the model information in a PostgreSQL database in containers is ordinary work and not in doubt.
- The part Artifactory does **not** provide (model pages, search, licence, safety-scan results) is what your database and web app are for (see "What Artifactory Does Not Provide").
- Conditions to settle:
  1. **The client-version gap (Q9, E3, E9).** You chose JFrog's `jf hf upload`. It needs Python 3 and a `huggingface_hub` that Artifactory supports (up to 1.19.0), while this project's CLI is pinned to 2.2 or newer. The import computer therefore needs a second, older environment.
  2. **Emulating an Artifactory that is not available (intent capture Q17 and Q22; Q11).** The emulation must answer the calls `upload_folder` makes (E8). That is a handful of calls, but the real system may behave differently in ways the documentation does not show.
  3. **Naming rules (E5).** Artifactory refuses organisation, model and revision names that Hugging Face allows elsewhere; some real model names or branch names may be rejected.
  4. **Size is undefined (Q5).** Disk, database and backup sizing cannot be fixed until someone gives a number.

| Question | Confidence | Why |
|----------|------------|-----|
| Can a model be put into Artifactory and fetched back with standard tools? | Medium-High | Documented upload and download paths (E1, E2); untested on your instance |
| Can the model information live in PostgreSQL and drive a portal? | High | Artifactory holds only a generated revision hash, not the model card or file metadata (E10); the information already exists in the download record |
| Can the new parts run in Docker Compose on one Linux server? | High | Docker is installed and the team is comfortable with it (Q4, Q8); no part needs more than a container |
| Can the Artifactory be emulated well enough to build and test against? | Medium | The upload uses about five kinds of call (E8); real-system differences are unknown |
| Can the design be finished within about a month? | High | A design-only plan with no code (Q7) |

## What Artifactory Provides

Everything below is from JFrog's documentation (E1 to E7) and was not tested on your instance.

| Capability | How it works | Notes |
|------------|--------------|-------|
| Hugging Face repository types | Local, remote and virtual repositories | A remote repository can only point at `https://huggingface.co`, so it is no use inside an air gap (E2, E7); the local type is the one that matters |
| The address clients use | `https://<platform>/artifactory/api/huggingfaceml/<repo-key>`, set as `HF_ENDPOINT` | Authenticates with an Artifactory token in `HF_TOKEN` (E1, E2) |
| Upload (deploy) | `HfApi.upload_folder(folder, repo_id, revision, repo_type)`, or `jf hf upload` which wraps it | The revision is the Git commit hash; re-deploying the same version overwrites it, and needs the Delete/Overwrite permission or Artifactory answers 409 (E2, E6) |
| Download (resolve) | `snapshot_download`, or libraries such as Transformers with `HF_HUB_ETAG_TIMEOUT` set, or `jf hf download` | Library resolution needs Artifactory 7.77 or newer and a client of 0.19.0 or newer (E2) |
| Models and datasets | Models from 7.77.1, datasets from 7.90.x | The intent statement speaks only of models, so datasets are not planned for |
| Large files | Xet protocol (faster, over 50 GB) or Git LFS | Xet works up to `huggingface_hub` 1.18.0, and 1.19.0 from Artifactory 7.173; it can be switched off, after which large files go through Git LFS (E3, E7) |
| Storage layout | The Machine Learning layout, default for new repositories since 7.111.x | The older layout is deprecated from June 2026, so a repository created now uses the new one (E4) |

## What Artifactory Does Not Provide

- **Model pages, search and model information.** The only metadata documented is a generated info file per package with a revision hash (E10). There is no mention of the model card, tags, licence, file sizes with checksums, or Hugging Face's safety-scan results. This matches your answer that Artifactory has "limited" Hugging Face API (intent capture Q5) and is why the database is needed.
- **The wider Hugging Face command set.** `jf hf` supports only `download` and `upload`; the native `huggingface-cli` commands (auth, cache, repo, spaces, collections and others) are not supported (E1).
- **Spaces.** Not supported (E7).
- **Client versions after 1.19.0.** Not supported (E3). This is the root of condition 1.

## The Client-Version Gap In Detail

- This project's `pyproject.toml` requires `huggingface_hub >=2.2,<3` (E9) because the download side needs its newer behaviour. That is a *download-from-Hugging-Face* need and has no reason to follow Artifactory's limit.
- The *upload-to-Artifactory* step is a different job. You chose `jf hf upload` for it (Q9). `jf hf` runs Python scripts that call `huggingface_hub` (E1), so the computer that runs the import needs three things: the JFrog CLI, Python 3, and a `huggingface_hub` no newer than 1.19.0.
- The air-gapped import computer can reach both Artifactory and the database (Q2). It would therefore carry the single-file `modelhub` program **and** that second environment. This is workable, but it is one more thing to install offline and keep matching, and it is the main reason to look hard at isolating the upload (a separate small container is the alternative you did not choose, Q9 option C; it stays an open design question).

## Emulating The Artifactory

The emulation is a build-and-test stand-in and is not delivered (intent capture Q24). It has to stand in for the Hugging Face upload and download calls and a few other Artifactory calls (intent capture Q22).

- Reading the installed `huggingface_hub` 2.2.0 shows that `upload_folder` uses: create a repository (`POST /api/repos/create`), ask which files need uploading (`POST /api/<type>s/<id>/preupload/<revision>`), the Git LFS batch call for large files (`POST <repo>.git/info/lfs/objects/batch`), the file transfer itself, and the commit (`POST /api/<type>s/<id>/commit/<revision>`). Listing uses the tree and paths-info calls (E8). About five kinds of call, so a stand-in is realistic.
- Limits of that evidence: it comes from version 2.2.0, not 1.19.0, which is the newest Artifactory supports, and it says nothing about Artifactory's own behaviour such as the 409 on overwrite, name checks, or Xet (E6, E5, E3). The emulation can be made to follow the documented rules, but whether it matches the real system stays unknown until a real instance is available (Q11 is "not known").

## Fit With Your Constraints

| Your answer | Effect on feasibility |
|-------------|------------------------|
| Docker Compose on one Linux server with Docker installed; the team is comfortable with containers (Q4, Q8, intent capture Q10) | No obstacle. The images must still be loaded without internet access, through the internal registry you named (Q1) |
| An internal container registry and central logging or monitoring exist (Q1) | The design must use them rather than invent its own |
| The import computer reaches both Artifactory and the database (Q2) | No import service is needed in front of the database |
| Licence must be kept and shown; a retention period applies (Q3) | Two requirements for the next stage; the retention period itself has no length yet |
| No other organisational limit; a design is needed within about a month (Q6, Q7) | Allows a thorough design stage |
| Already-imported same-version models are skipped, the rest of the list continues (Q10, Q13) | A rule the import must follow; Artifactory's own overwrite behaviour (E6) points the other way, so the import must check first |
| Existing folder models are imported too (Q12) | An import path from the old folder store is part of the work |

## Evidence

All read on 12 October 2026.

- E1: JFrog, "Use Hugging Face with JFrog CLI" (docs.jfrog.com/artifactory/docs/use-hugging-face-with-jfrog-cli).
- E2: JFrog, "Hugging Face Repositories" (docs.jfrog.com/artifactory/docs/hugging-face-repositories), the sections on creating, connecting, deploying and resolving.
- E3: The same page, "Hugging Face Limitations in Artifactory" and "Limitations of Xet Protocol in Artifactory".
- E4: The same page, "Hugging Face Repository Structure (Legacy)" and "Migrate Legacy Hugging Face Repositories".
- E5: The same page, naming restrictions for organisations, models and revisions.
- E6: The same page, the repository-structure notes on overwriting a version and the 409 response.
- E7: The same page, Spaces, the remote repository URL, and disabling Xet.
- E8: The installed `huggingface_hub` 2.2.0 source (`hf_api.py`, `_commit_api.py`, `lfs.py`), searched for the endpoints it builds.
- E9: This project's `pyproject.toml` (`huggingface_hub>=2.2,<3`).
- E10: The same JFrog page, the repository-structure notes naming `.jfrog_huggingface_model_info.json` and the property `huggingfaceml.generated.revision.sha1`.

## Assumptions And Open Questions

- The real Artifactory behaves as JFrog's documentation says, including the naming rules and overwrite behaviour; none of this was tested [assumption]
- The Artifactory version is at least 7.77.1 and a local Hugging Face repository using the Machine Learning layout can be created on it [assumption]
- The air-gapped import computer can have the JFrog CLI, Python 3 and a `huggingface_hub` of 1.19.0 or older installed offline, next to the single-file `modelhub` program [assumption]
- The storage size to plan for is the earlier planning figure (up to about 1,000 models with up to 10 versions each, some over 100 GB) until a number is given (Q5) [assumption]
- The retention period in Q3 has no length yet [assumption]
