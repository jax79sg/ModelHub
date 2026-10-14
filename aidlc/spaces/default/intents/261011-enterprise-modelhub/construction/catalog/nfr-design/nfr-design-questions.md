# NFR Design Questions: catalog

Context: "NFR design" turns the approved quality targets into concrete patterns. Most of the Catalog's follow from the targets (a summary table for the list, keyed hash for tokens, a pool of 10 database connections, a 5-second query limit, ready check with the database critical). Two choices have real alternatives.

## Q1. Should the Catalog cache the models list in memory?

Why we ask: the list target (under 1 second for 95% of requests at 1,000 models and 20 people at once) is met by one narrow table with indexes; a cache would be faster still but can show a model late, which the requirement NFR1 (findable at once) does not want.

- Option A, no cache; every list reads the summary table. Pros: always current; nothing to invalidate; simplest. Cons: each request costs a query (small).
- Option B, a 10-second in-memory cache of list answers. Pros: absorbs repeated identical requests. Cons: a newly imported model can be missing for 10 seconds; the cache must be cleared after each store and removal; more to test.
- Recommendation: A.

A. Option A: no cache
B. Option B: 10-second cache
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. How should the documents be held in the database?

Why we ask: documents (README, pictures up to 7 MB, saved responses, manifests) are stored in the same transaction as the record (functional design, FDQ3 A). The database offers two ways.

- Option A, an ordinary binary column in a separate table, read in one piece (up to 16 MiB each). Pros: simple; transactional; the usual choice for documents of this size; the list never touches the table. Cons: the whole document is read into memory when served (at most 16 MiB).
- Option B, PostgreSQL large objects, streamed in blocks. Pros: streaming of big content. Cons: harder to back up and clean up; a separate removal step; unusual for documents this small.
- Recommendation: A.

A. Option A: binary column in a separate documents table
B. Option B: large objects, streamed
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A
