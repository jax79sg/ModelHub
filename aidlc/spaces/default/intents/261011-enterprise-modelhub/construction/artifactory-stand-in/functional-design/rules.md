# Rules: artifactory-stand-in

The stand-in has no business rules of its own. These rules say how it imitates Artifactory, and where a rule is an assumption rather than JFrog's documented behaviour it says so and points at the `Assumption` entity (`entities.md`). Sources are requirement and contract IDs plus the answers in `functional-design-questions.md` (FDQ).

```yaml
unit: artifactory-stand-in
rules:
  - id: BR1.1
    statement: Every call must carry the one configured bearer token; with a wrong or missing token the stand-in answers 401, and with the right token but write permission switched off it answers 403 to every call that changes something.
    category: authorization
    applies_to: [StandInServer]
    trigger: any call received
    logic: "IF the bearer token is missing or differs from token THEN answer 401 with code 'unauthorised' and no detail. ELSE IF the call changes state (create, pre-upload, large-file batch, upload of an object, commit, delete) AND write_allowed is false THEN answer 403."
    violation: not applicable (the rule is the refusal)
    source: [FR7.1, FR7.2, C5, FDQ5 A]
  - id: BR1.2
    statement: Organisation, model and revision names that break JFrog's documented naming rules are refused before anything is stored.
    category: validation
    applies_to: [StoredVersion]
    trigger: create-repository, pre-upload or commit call that names a version
    logic: "IF the organisation is not letters, numbers and single hyphens, or starts or ends with a hyphen, or is all digits, OR the model has anything other than letters, numbers, hyphen, underscore, period, OR the revision has anything other than letters, numbers, hyphen, period THEN answer 400 with a readable message naming the field, and store nothing."
    violation: the 400 answer; the exact code and body are an assumption (invented), listed on the checklist
    source: [FR7.2, C5 names]
  - id: BR1.3
    statement: A repeat upload of a version that is already complete is refused with 409 unless overwrite is allowed.
    category: constraint
    applies_to: [StoredVersion]
    trigger: commit call for (organisation, model, revision) whose state is complete
    logic: "IF a complete version with the same name and revision exists AND overwrite_allowed is false THEN answer 409 and leave the version unchanged. IF overwrite_allowed is true THEN replace its files with the new set."
    violation: the 409 answer; the body is an assumption on the checklist
    source: [FR7.2, C5 overwrite, NFR4]
  - id: BR1.4
    statement: A committed version's revision is a 40-character hexadecimal commit hash, and the stand-in returns it from the commit call.
    category: calculation
    applies_to: [StoredVersion]
    trigger: commit call
    logic: "The revision is the SHA-1 of the sorted list of '<path> <sha256>' lines of the version's files, written as 40 hexadecimal characters. A client that asked for a named revision, such as 'main', gets that name mapped to the hash; listing by hash or by name returns the same files."
    violation: not applicable
    source: [FR7.2, FR1.1]
  - id: BR1.5
    statement: A version becomes visible to listing and fetching only when its commit call succeeds, so a repeat after any stop finds it complete or absent, never half there.
    category: constraint
    applies_to: [StoredVersion]
    trigger: any upload call; commit call; listing call
    logic: "Files received before the commit belong to a partial version, which listing and fetch treat as absent (404). The commit moves the whole version to complete in one step. A failed or cut commit leaves the version partial, and a later commit or delete for it works."
    violation: not applicable
    source: [C5 timeouts table, NFR4, FR1.5]
  - id: BR1.6
    statement: A file's checksum must match what was declared for it.
    category: validation
    applies_to: [StoredFile]
    trigger: upload of an object; commit call
    logic: "IF the file is kept AND the SHA-256 of the received content differs from the declared sha256 THEN answer 422 and do not store the file. For a virtual file the declared sha256 and size are taken as given."
    violation: the 422 answer; the status is an assumption (inferred)
    source: [FR7.1, C5]
  - id: BR1.7
    statement: Listing a complete version returns each file's path, size and checksum, in the active layout.
    category: policy
    applies_to: [StoredVersion, StoredFile]
    trigger: tree, paths-info or storage-listing call
    logic: "Answer with every file of a complete version: path, size_bytes, sha256. The Hugging Face tree call always answers in one fixed shape; the Artifactory storage-style listing answers with the paths of the active layout (BR1.12). A partial or absent version answers 404."
    violation: 404 for partial or absent
    source: [FR7.1, C5 other_calls_needed]
  - id: BR1.8
    statement: Deleting a version removes all its files, and deleting a version that is not there is answered 404.
    category: constraint
    applies_to: [StoredVersion]
    trigger: delete call
    logic: "IF the version exists in any state THEN remove it and its files and answer 204. IF it does not exist THEN answer 404. A delete needs write permission (BR1.1)."
    violation: not applicable
    source: [FR7.1, FR5.5, C5]
  - id: BR1.9
    statement: Files up to the keep limit are held with their content; larger files, and files the test did not mark keep, are held as name, size and checksum only.
    category: policy
    applies_to: [StoredFile]
    trigger: upload of an object
    logic: "IF size_bytes is at most keep_limit_bytes OR the test marked the path keep THEN content_mode is kept and the content is held in the temporary folder. ELSE content_mode is virtual and the content is discarded as it arrives. A fetch of a virtual file answers 501 with 'content not kept'; it never returns invented bytes."
    violation: the 501 answer
    source: [FDQ2 C, NFR7]
  - id: BR1.10
    statement: A failure switch fires on the matching call after the stated number of calls, for the stated number of times, and then clears unless it is sticky.
    category: policy
    applies_to: [FailureSwitch]
    trigger: any call received
    logic: "Count the calls that match the switch's scope. When the count passes after_calls, apply the switch's effect to the call: unauthorised 401, forbidden 403, conflict 409, name-refused 400, server-error 500, slow (hold the answer for the stated time), cut-transfer (close the connection after half the body), half-version (store half the files of the commit, then answer 500). Decrement times; remove the switch at zero unless sticky. Switches are checked before any other rule."
    violation: not applicable
    source: [FDQ4 A, NFR4, C5 timeouts table]
  - id: BR1.11
    statement: Every call is recorded for the test to read, but the record never holds the token or the content of kept files.
    category: policy
    applies_to: [RecordedCall]
    trigger: any call answered
    logic: "Append sequence, method, path, status, UTC time and the name of the switch that fired. Never store the Authorization header or any body."
    violation: not applicable
    source: [FR7.1, NFR5b]
  - id: BR1.12
    statement: The stand-in lays out the Artifactory storage-style listing in one of two invented layouts, chosen when it starts, so the gateway's path discovery is tested without the stand-in claiming to know the real one.
    category: policy
    applies_to: [StandInServer, StoredFile]
    trigger: storage-listing call
    logic: "layout flat answers paths '<org>/<model>/<revision>/<file>'. layout nested answers '<org>/<model>/revisions/<revision>/files/<file>'. The layout never changes while running. Both are recorded as invented assumptions on the checklist."
    violation: not applicable
    source: [FDQ3 A, C5 other_calls_needed, X1]
  - id: BR1.13
    statement: Every behaviour that JFrog's documentation does not state is written in the assumption register and, where it must be confirmed, on the checklist; a behaviour without an entry fails the stand-in's own test.
    category: policy
    applies_to: [Assumption, ChecklistItem]
    trigger: building and testing the stand-in
    logic: "The register is one data file with an entry per assumed behaviour: id, behaviour, basis (documented, inferred or invented), source, and whether it needs confirming. The checklist is produced from the entries needing confirmation. A test lists every answer the stand-in can give and fails if one has no register entry."
    violation: the stand-in's own test fails
    source: [FR7.2, FR7.3, R2, R3]
  - id: BR1.14
    statement: The stand-in starts empty for each test, listens only on the local machine, uses no real credentials, and is never part of what is delivered.
    category: constraint
    applies_to: [StandInServer]
    trigger: start; packaging
    logic: "On start, create a fresh temporary folder and empty state, pick a free port and bind to 127.0.0.1 only. Never read the environment for real tokens: the token is passed by the test. On stop, delete the folder. The delivered images and the single-file program do not include it, and a check in the platform unit fails if they do."
    violation: refuse to start if the bind address is not local
    source: [FR7.1, ADR-009, AC7.1, NFR9, FDQ6 A]
  - id: BR1.15
    statement: An upload whose file path would leave the version's folder is refused.
    category: validation
    applies_to: [StoredFile]
    trigger: pre-upload, large-file batch, commit
    logic: "IF the path is empty, absolute, contains '..' as a part, contains a backslash, or has a drive letter THEN answer 400 and store nothing."
    violation: the 400 answer
    source: [corner checklist: escaping the root, NFR5]
  - id: BR1.16
    statement: The only calls the stand-in answers are the ones the system makes; any other call is answered 404 and recorded.
    category: policy
    applies_to: [StandInServer]
    trigger: any call to an unknown path
    logic: "Answer 404 with code 'not_imitated' and record the call, so a library that starts making a new call is noticed by the tests instead of being silently accepted."
    violation: not applicable
    source: [FDQ1 A, FR7.1]
```

## Rules Summary

| ID | Rule | Category |
|----|------|----------|
| BR1.1 | One bearer token; 401 wrong, 403 no write | authorization |
| BR1.2 | Naming rules refused with 400 | validation |
| BR1.3 | Repeat of a complete version: 409 | constraint |
| BR1.4 | Revision is a 40-character hash | calculation |
| BR1.5 | Visible only after commit | constraint |
| BR1.6 | Checksum must match | validation |
| BR1.7 | Listing shows path, size, checksum | policy |
| BR1.8 | Delete removes all; absent gives 404 | constraint |
| BR1.9 | Keep small files, virtual large ones | policy |
| BR1.10 | Failure switches | policy |
| BR1.11 | Calls recorded without secrets | policy |
| BR1.12 | Two invented layouts | policy |
| BR1.13 | Assumption register and checklist | policy |
| BR1.14 | Empty, local, never delivered | constraint |
| BR1.15 | Path escape refused | validation |
| BR1.16 | Unknown calls get 404 | policy |
