# Functional Design Questions: catalog

Context: `catalog` is the only part that reads or writes model information, the stored documents, the import trail and the personal tokens (decision ADR-002). It is a service with an HTTP interface (contracts C2 and C3, already written) and a PostgreSQL database that it alone owns. Its requirements are FR2 to FR2.8, FR3.4, FR3.5, FR4.4 and FR4.5, plus the speed target NFR2 (the models list in under 1 second at 1,000 models, up to 10 versions each). The interface shapes are fixed by the contracts; the questions are about what is behind them.

## Q1. How should text search match?

Why we ask: this is open question "whole words or parts of words, and in which languages?" from the requirements (FR3.5, AC3.3). The model cards are mostly English but include names, code and other languages.

- Option A, whole-word search using the database's full-text search with English word forms (so "quantize" finds "quantized"), plus a match on model id and tags; other languages match whole words as written. Pros: ranked, fast, standard; matches AC3.3. Cons: a part of a word (such as "gguf" inside "tinyllama-gguf-q4") is found only through the model id and tags.
- Option B, substring search (any part of a word, via trigram indexes). Pros: finds everything typed. Cons: noisy results; larger indexes; slower on long cards.
- Option C, A first, and B only for model ids and tags. Pros: precise on the card text, forgiving on names. Cons: two paths to test.
- Recommendation: C.

A. Option A: whole words, English word forms
B. Option B: any part of a word
C. Option C: A for card text; parts of words for model ids and tags
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q2. How should the models list stay fast?

Why we ask: NFR2 needs under 1 second, and the list must never read the stored documents (contract C2).

- Option A, a summary row for each model's latest version, holding only the fields the list shows and filters on, written in the same transaction as the version. Indexes on each filter and sort field. Pros: the list reads one narrow table; simple to prove against the target. Cons: one more table to keep consistent (the transaction does it).
- Option B, compute the latest version on each request from the full version rows. Pros: no extra table. Cons: slower, and harder to keep under the target as versions grow.
- Recommendation: A.

A. Option A: summary row per model, updated in the same transaction
B. Option B: compute on each request
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. Where should the stored documents live?

Why we ask: documents are the README, pictures (up to 7 MB each), saved Hugging Face responses, the checksum manifest and the signed bundle files (FR2.2). The record and its documents must be stored together or not at all (FR2.5). Model files themselves stay in Artifactory and are never here.

- Option A, inside the PostgreSQL database, in the same transaction as the record. Pros: one transaction covers everything (FR2.5, AC2.1); one backup and one data volume to look after. Cons: the database grows by the documents' size; fine at the planned size (about 1,000 models).
- Option B, as files on the data volume, with only their names and checksums in the database. Pros: a smaller database. Cons: a crash can leave files without rows or rows without files; needs a clean-up job; two things to back up.
- Recommendation: A.

A. Option A: inside the database
B. Option B: as files, with the database holding names and checksums
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. How does the Catalog tell "the same record again" from "a different record"?

Why we ask: contract C2 says a repeat of the same record changes nothing (answer 200) and a different record for the same model and commit is refused with 409 (FR1.4, FR1.8).

- Option A, the Catalog computes one checksum over the record (fields, file list, import-trail fields except the time of the call) and over each document's checksum, and stores it with the version; a repeat is the same if the checksum is equal. Pros: simple and exact. Cons: any change to what the importer sends, even a harmless extra field, makes a repeat look different, so the format must be versioned.
- Option B, compare the fields one by one. Pros: can ignore chosen fields. Cons: more code and more ways to get it wrong.
- Recommendation: A.

A. Option A: one stored checksum of the record and documents
B. Option B: compare field by field
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. How should personal tokens be made and checked?

Why we ask: FR4.4 and FR4.5 say the value is shown once and only a hash is stored. The choice is how to hash.

- Option A, a random 256-bit value with a recognisable prefix, stored as a keyed hash (HMAC-SHA-256) using the `token_hash_pepper` secret from contract C7; checked by hashing what is presented and comparing. A last-used time is updated at most once a minute. Pros: fast on every import call; a stolen database alone cannot be used to check guesses without the pepper. Cons: losing the pepper invalidates every token (people make new ones).
- Option B, a slow password hash (such as argon2). Pros: the usual choice for human passwords. Cons: needless for a 256-bit random value; adds delay to every import call.
- Recommendation: A.

A. Option A: random 256-bit value, keyed hash with the pepper
B. Option B: slow password hash
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q6. What stays when a version is marked removed?

Why we ask: Retention removes the files from Artifactory and then asks the Catalog to mark the version removed (contract C2). The trail rows must stay. The question is the rest.

- Option A, keep everything (record, files list, documents, trail) and set a state `removed` with a time and who decided. The portal shows it as removed, with the card still readable. Pros: nothing is lost; simplest; the history stays complete. Cons: the documents' space is not freed (small).
- Option B, delete the documents (README, pictures, saved responses) and keep the record, file list and trail. Pros: frees space. Cons: the card of a removed version can no longer be shown; a loss that cannot be undone.
- Recommendation: A.

A. Option A: keep everything, set state removed
B. Option B: delete the documents, keep the rest
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: B
