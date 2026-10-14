# Functional Design Questions: import-cli

Context: `import-cli` is the change to the existing command-line program so it can import into the enterprise store. It keeps the person's personal token, checks a bundle with the code that already exists, sends it to the import service piece by piece (contract C1), shows progress and prints the report. It does not talk to Artifactory or the database (decision ADR-001). The existing commands `pull`, `bundle`, `verify`, `unpack`, `list` and `key` keep working. Requirements: FR1, FR1.2, FR1.9 to FR1.11, FR1.13, FR8, FR8.1, NFR10. Exit statuses stay 0 (all imported or skipped), 1 (at least one model failed) and 2 (could not run).

## Q1. What should the new commands look like?

Why we ask: this is the surface people will learn. Importing from a bundle and importing from an old model-store folder (FR8) are two sources for one action.

- Option A, one new command `modelhub import` that takes bundles (first piece, or a folder of bundles) and, with `--from-store <folder>`, the models of an old model-store folder; plus `modelhub login` and `modelhub logout` for the token. Pros: one action, one report; the same rules whatever the source. Cons: the command has two modes.
- Option B, two commands: `modelhub import` for bundles and `modelhub import-store` for the old folder. Pros: each command is simple. Cons: two names for one action; the report and flags are duplicated.
- Recommendation: A.

A. Option A: `import` (with `--from-store`), `login`, `logout`
B. Option B: `import` and `import-store`
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. How does the CLI hold the token and the server address?

Why we ask: the person makes a personal token in the portal and pastes it into the CLI (FR1.2). The token must never be printed (FR1.11) and a command line is saved in shell history, so it should not be typed as a flag.

- Option A, `modelhub login` asks for the server address and the token (the token is typed hidden, or read from standard input for scripts) and saves them in a file in the person's own settings folder that only they can read (permissions 600 on Linux; the person's own profile folder on Windows). `MODELHUB_SERVER` and `MODELHUB_TOKEN` environment variables override the file for scripts. The token is never accepted as a command-line flag. Pros: typed once; safe from history; scripts still work. Cons: a token sits in a file (readable only by the person).
- Option B, environment variables only. Pros: nothing stored by the tool. Cons: people put them in shell profiles, which are less protected and often copied.
- Option C, ask every time. Pros: nothing stored. Cons: unusable for a list of models and for scripts.
- Recommendation: A.

A. Option A: `login` saves them in a private file; environment variables override
B. Option B: environment variables only
C. Option C: ask every time
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. How should the pieces be sent?

Why we ask: files over 100 GB may be sent over a slow link, and the import must resume after any stop (NFR4). Contract C1 sends one piece per request.

- Option A, one piece at a time, in order, with progress shown per piece and per byte; on a rerun, only the pieces the service reports missing are sent. Pros: simple; memory use is one read buffer; easy to reason about. Cons: does not use a fast link fully.
- Option B, up to 4 pieces at the same time (a setting). Pros: faster on a fast link. Cons: more code, harder progress display, more load on the service; the service also limits imports.
- Recommendation: A.

A. Option A: one piece at a time
B. Option B: up to 4 at the same time
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. What should the CLI do when the service says it is busy?

Why we ask: the service allows only a few imports at once and answers `service_busy` (retryable) when full (service design). The usual network retry waits at most 16 seconds, which is too short for an import that can last hours.

- Option A, treat it like a network error: 5 tries at 1, 2, 4, 8 and 16 seconds, then fail that model and carry on. Pros: one rule. Cons: a model fails only because the service was busy for half a minute.
- Option B, wait and poll every 60 seconds for up to 30 minutes (settings), showing "waiting for a free place", then fail that model with a clear message. Pros: matches how long imports last. Cons: a list of models may wait a long time on one.
- Recommendation: B.

A. Option A: the same five short retries as for network errors
B. Option B: wait up to 30 minutes, polling every 60 seconds
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q5. How should the old model-store folder be imported, given it has no signature?

Why we ask: the service accepts only a bundle signed by a trusted key (FR1.14), and the old folder was made by `unpack`, which verified the original bundle but kept no signature. The signing key of the online side is not on the import computer.

- Option A, the CLI makes a new bundle from the folder's models into a temporary folder and signs it with a key made on the import computer (`modelhub key create`); an administrator adds that key's fingerprint to the service's trusted list once, after confirming it. The trail then names that key's fingerprint. Pros: one check path for both sources; the trust decision is explicit and visible. Cons: needs temporary disk space about the size of the model; an administrator step per import computer; the signature then proves "this computer's owner vouched for it", not that it came from the online side.
- Option B, send the folder's files unsigned, marked as "from the old folder", and let administrators allow that per import computer. Pros: no temporary copy; no re-bundling. Cons: a second, weaker path in the service; the signed manifest check does not apply.
- Option C, leave the old folder out for now (stay as designed but not built until a need is shown). Pros: nothing weak is built. Cons: the old models cannot be imported.
- Recommendation: A.

A. Option A: re-bundle and sign with a key made on the import computer
B. Option B: send unsigned, marked "from the old folder"
C. Option C: leave the old folder out for now
D. Not yet defined
X. Other (please specify)

[Answer]: C
