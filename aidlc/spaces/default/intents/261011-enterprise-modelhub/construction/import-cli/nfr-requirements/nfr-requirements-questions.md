# NFR Requirements Questions: import-cli

Context: "NFR" means quality targets. This is the import command added to the existing program. Already settled: it behaves the same on Linux and Windows and needs nothing installed beyond the program or its offline pack (NFR10); memory at or below 8 GB at peak for any file size (NFR7); retries at 1, 2, 4, 8 and 16 seconds; exit statuses 0, 1 and 2. One technical choice is yours.

My defaults for this unit (not questions): one piece is sent at a time in blocks of at most 8 MiB; progress shows after 2 seconds; the token file is readable only by its owner; the token is never printed; the program makes no connection except to the configured server; the program is built for the same systems as today (Linux x86-64, Windows, macOS on Apple silicon) and the offline packs keep working.

## Q1. Which library should the CLI use to talk to the import service?

Why we ask: sending pieces of several gigabytes as a stream with progress needs a capable HTTP library. The program already includes one (the Hugging Face library it uses is built on httpx), so the choice is between reusing it and adding another.

- Option A, httpx (already installed through huggingface_hub). Pros: no new dependency for the single-file program or the offline packs; supports streaming uploads and timeouts well. Cons: the program depends on its version staying compatible with huggingface_hub's range.
- Option B, requests. Pros: very familiar. Cons: a new dependency in the program and in every offline pack; streaming a large body with progress is clumsier.
- Option C, the standard library only. Pros: nothing to add. Cons: we would write timeouts, TLS handling and streaming ourselves.
- Recommendation: A.

A. Option A: httpx
B. Option B: requests
C. Option C: standard library only
D. Not yet defined
X. Other (please specify)

[Answer]: A
