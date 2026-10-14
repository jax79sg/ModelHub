# Functional Design Questions: artifactory-stand-in

Context: the stand-in is a small program that imitates Artifactory's Hugging Face repository so the rest of the system can be built and tested with no real Artifactory (requirements FR7.1 to FR7.3, NFR9; contract C5). It is never delivered. It has no business rules of its own; its design is a list of what it answers, what it remembers, and what it gets wrong on purpose so tests can see failures. The Artifactory facts it follows come from JFrog's documentation and are not tested on a real instance (C5), so everything it assumes is written down.

The engine picked this unit first among the units with no dependencies (`common` and this one can go in either order). Sizes and calls below come from the installed `huggingface_hub` library: `upload_folder` makes five kinds of call (create repository, pre-upload check, large-file batch, commit, then reads of the tree), and `snapshot_download` reads the tree and fetches files.

## Q1. How much of the Hugging Face interface should the stand-in imitate?

Why we ask: this sets its size and how closely it follows the real thing.

- Option A, only the calls our system makes: the five upload calls, reading a version's tree and file list with checksums, fetching a file, and deleting a version, as `jf hf upload`, `snapshot_download` and our gateway use them. Pros: small; every call has a reason; matches FR7.1. Cons: a new library version that makes an extra call fails the tests, which is a useful warning.
- Option B, the whole Hugging Face Hub API. Pros: nothing is missing. Cons: far more than is needed; Artifactory itself supports only part of it, so it would imitate things Artifactory does not do.
- Option C, no HTTP at all: replace the gateway's Python interface with a fake. Pros: simplest. Cons: the real `jf hf upload` and library calls are never exercised, which is the main risk (R1, R2).
- Recommendation: A.

A. Option A: only the calls our system makes
B. Option B: the whole Hub API
C. Option C: no HTTP, fake the gateway interface
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. Where should the stand-in keep what it is sent?

Why we ask: test packages can include files of huge size (the earlier 1 TiB test used a "stand-in object" instead of a real file), and a test should not need that much disk.

- Option A, real files in a temporary folder, deleted after the test. Pros: simple; checksums are real. Cons: a test of a very large file needs the disk space.
- Option B, remember only each file's name, size and checksum, and throw the content away, except for files marked "keep" (such as small README files). Pros: huge files cost nothing. Cons: a fetch of a thrown-away file can only return a generated pattern, and a test of that content must mark the file "keep".
- Option C, both: B by default for files above a size limit (default 1 MiB), A below it. Pros: small files behave like real ones and large files are free. Cons: two paths to test.
- Recommendation: C.

A. Option A: real files in a temporary folder
B. Option B: remember only name, size and checksum
C. Option C: both, switched by size
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q3. How should the stand-in handle the unknown layout of the Machine Learning repository?

Why we ask: JFrog's pages do not say where files are stored in the Machine Learning layout, so our gateway discovers paths by listing (open question X1). The stand-in must let the gateway's discovery be tested, without pretending to know the real layout.

- Option A, the stand-in can run with more than one invented layout (for example `<org>/<model>/<revision>/<file>` and a nested variant), chosen by a setting, and tests run the gateway against both. Pros: proves the gateway does not depend on one layout. Cons: more to build.
- Option B, one invented layout, with the guess recorded as an assumption. Pros: simplest. Cons: the gateway could quietly depend on it.
- Recommendation: A.

A. Option A: more than one layout, chosen by a setting
B. Option B: one invented layout
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. Should the stand-in be able to misbehave on request?

Why we ask: our import must survive failures (NFR4, contract C5's table of timeouts and retries), and those failures cannot be produced by a well-behaved imitation.

- Option A, yes: switches for 401 and 403, 409 on overwrite, name-rule refusals, a server error on the Nth call, a slow call, a stopped transfer partway through a file, and a repeat that finds the version half there. Switches are set by the test, per repository or per call. Pros: tests the restart and error paths from the contract. Cons: more to build and to document.
- Option B, no: tests that need failures patch the gateway. Pros: simpler stand-in. Cons: the real libraries' reaction to a failure is never tested.
- Recommendation: A.

A. Option A: yes, switches for the failures in the contract
B. Option B: no
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. What sign-in should the stand-in demand?

Why we ask: the real Artifactory demands a bearer token (C5); a stand-in that accepts anything cannot catch a missing token.

- Option A, one configured token; any other or no token gets 401, and the test can change what the token may do (403 for no write permission). Pros: catches a missing or wrong token. Cons: slightly more setup.
- Option B, accept anything. Pros: simplest. Cons: hides a whole class of defect.
- Recommendation: A.

A. Option A: one configured token; 401 and 403 are possible
B. Option B: accept anything
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q6. How do tests start it?

Why we ask: this fixes how it is packaged inside the test code (and shows the `platform` unit whether it needs an image for it: it does not, the stand-in is not delivered).

- Option A, started inside the test run as a small local web server on a free port, and stopped when the test ends. Pros: no container needed; fast; works on the build machines that run the tests. Cons: not the same environment as the real thing.
- Option B, as a container started by the test run. Pros: closer to the real server. Cons: needs Docker on every build machine; slower.
- Option C, both. Pros: either as needed. Cons: more to maintain.
- Recommendation: A.

A. Option A: inside the test run, on a free local port
B. Option B: as a container
C. Option C: both
D. Not yet defined
X. Other (please specify)

[Answer]: A
