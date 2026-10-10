# Requirements

Sources: your request and answers in `intent-statement` (`ideation/intent-capture/`), the feasibility documents in `ideation/feasibility/` (`feasibility-assessment.md`, `constraint-register.md`, `raid-log.md`), the affirmed practices in `team-practices` (`inception/practices-discovery/`), and your answers Q1 to Q12 in `requirements-analysis-questions.md`. IDs such as FR2.1 are permanent: later steps must reuse them.

## Intent Analysis

You are building a command-line tool with two halves. On a computer with internet access, it downloads public Hugging Face models and everything needed to display a model page. It then packs that into pieces small enough for your transfer drives. Inside the air-gapped environment, the same tool checks the pieces, puts them back together, and lists what is available, so a separate web app (built later) can show each model as huggingface.co does.

- Goal behind the features: a model page and its files must arrive in the air-gapped environment complete, undamaged, and provably the same as what Hugging Face served (`intent-statement`, Q2 and Q3).
- Scale: many models, some over 100 GB each, moved on drives that can be smaller than 1 GB (feasibility Q5, Q9).
- Decision from this step: the full scope below is wanted, and **the go-live date can move instead of dropping scope** (Q12). This replaces the one-month deadline as a fixed limit (feasibility Q10).

## Functional Requirements

### FR1 Choosing models

- FR1.1 The tool accepts one public model identifier (for example `org/name`) in a single command. [Q2]
- FR1.2 The tool accepts a file listing many model identifiers, one per line, and fetches them all in one run. [Q2]
- FR1.3 The tool records the exact version (commit identifier) of every model it fetches, and the user can name a branch, tag or commit to fetch; the default is the main branch. [Q2, CO-3 in `constraint-register.md`: the approval step needs to know exactly what was fetched]
- FR1.4 For a private or gated model, the tool stops for that model with a message naming it and saying it is not supported, and continues with the remaining models in a list. [Out of scope in `intent-statement`; a defined behaviour at that boundary]

Acceptance:
- Given a list file with three public models and one gated model, when the tool runs, then the three public models are fetched and the gated one is reported as unsupported, and the run ends with a non-zero status.
- Given a model identifier that does not exist, when the tool runs, then it reports that the model was not found and fetches nothing for it.

### FR2 Choosing files by type

- FR2.1 Before downloading, the tool lists the model's files grouped by type, with a plain-language explanation of each type, the size of each type, and the total size. [Q1, Q10]
- FR2.2 The user can select one or more file types to download. [Q1]
- FR2.3 When the user selects no types, the tool shows the list from FR2.1 and stops without downloading anything. [Q10]
- FR2.4 In a run over a list of models, the user gives the type selection once for the run, and it applies to every model. When no selection is given, the tool shows the types found across the models and stops without downloading anything. [Q2, Q10; combined behaviour is derived, see assumption A5]
- FR2.5 A model's small settings and text files and its README are always fetched, whatever types are selected, because the web app needs them. [Q3 A; derived, see assumption A6]

Acceptance:
- Given a model with two weight formats, when the user selects only the first, then only that format (plus the files in FR2.5) is downloaded.
- Given no selection, when the tool runs, then no file is downloaded and the exit status is zero.
- Given a selection that matches no file of a model, when the tool runs, then it reports that nothing matched for that model.

### FR3 Information for the model page

- FR3.1 The tool keeps the README text and its settings header (licence name, language, tags). [Q3 A]
- FR3.2 The tool keeps the summary details Hugging Face gives for the model: task type, library, dates, download and like counts, size, and parameter counts. [Q3 B]
- FR3.3 The tool keeps the full file list with sizes and checksums, and Hugging Face's own safety-scan results for each file, as they were at capture time. [Q3 C]
- FR3.4 The tool keeps the change history and the named versions (branches and tags). [Q3 D]
- FR3.5 Every item kept is stored in the form Hugging Face returned it, and the time it was captured is recorded, because counts and scan results change. [Q3; `feasibility-assessment.md`]
- FR3.6 The tool keeps the licence name from the settings header and, when the repository contains a licence file, that file. When neither exists, the tool records that licence text was not available. [feasibility Q6 and CR-2 in `constraint-register.md`]

Acceptance:
- Given a public model, when it is fetched, then the kept items include the README, the summary details, the file list with checksums, the change history, and the capture time of each.
- Given a model with no licence file, when it is fetched, then its record says licence text was not available and still holds the licence name if one exists.

### FR4 Pictures in the README

- FR4.1 The tool finds pictures the README refers to. Pictures stored in the model's own repository are already part of the files fetched. [Q4]
- FR4.2 The tool downloads pictures hosted on other websites, stores them with the model, and writes a second README whose picture references point to the local copies. The original README is kept unchanged. [Q4 A]
- FR4.3 When a picture cannot be fetched, the tool leaves that reference unchanged in the second README and lists the failed picture in the run record. [Q4; corner: part of the work failed]
- FR4.4 The tool only fetches pictures over web addresses starting `http://` or `https://`, and refuses any picture larger than a documented size limit, reporting it as skipped. [Q4; corner: untrusted content; the limit's value is set in design]

Acceptance:
- Given a README with one picture on another website, when the model is fetched, then the picture is stored locally and the second README points to it.
- Given a picture address that returns an error, when the model is fetched, then the model still completes and the run record lists the picture as failed.

### FR5 Downloading

- FR5.1 The tool downloads files through Hugging Face's official libraries or command-line tool, and never by scraping web pages. [request; CT-4]
- FR5.2 The tool downloads large files using Hugging Face's official fast-transfer route, and several files at the same time. [Q9, Q11; CT-6 in `constraint-register.md`]
- FR5.3 After an interruption, a re-run completes the job without downloading again any file already verified as complete. [Q5 of the feasibility answers: models over 100 GB; corner: killed mid-work. Derived, see assumption A7]
- FR5.4 The tool checks every downloaded file against the checksum Hugging Face reports for it, and treats a mismatch as a failure for that file. [CO-3; E4 in `feasibility-assessment.md`]
- FR5.5 The user may supply a Hugging Face access token. When Hugging Face says the request limit has been reached, the tool waits as long as it is told, retries, and tells the user it is waiting. [CT-8; E9]

Acceptance:
- Given a download stopped half-way through a set of files, when the tool is run again, then no completed file is fetched again and the run finishes.
- Given a file whose checksum does not match, when the tool checks it, then that file is reported as failed and is not counted as complete.

### FR6 Bundling and splitting

- FR6.1 The tool packs everything fetched for a model into a bundle that includes a manifest listing every file with its size and checksum, the exact commit, the capture time, and the tool version. [CO-3; R4 in `raid-log.md`]
- FR6.2 The user can set a maximum piece size when creating a bundle, and the tool cuts the bundle into pieces no larger than that. [Q5 A]
- FR6.3 In interactive mode, the user gives the size of each drive in turn. The tool fills a drive, says when to swap it, and continues until everything is written. [Q5 B]
- FR6.4 The piece size can be set below 1 GB; the smallest value the tool accepts is documented and is below 1 GB. [feasibility Q9]
- FR6.5 Each piece carries its own checksum and its position in the whole, so one piece can be checked alone, and a missing or damaged piece is found and named without re-copying the others. [CO-2 in `constraint-register.md`]
- FR6.6 A piece being written is never left looking complete if the write stops early. [corner: half-written file]
- FR6.7 Before writing, the tool states the total size and the number of pieces, and refuses to start when the destination does not have enough free space. [corner: disk full]
- FR6.8 A repository path that cannot be written on Windows (reserved names, forbidden characters, too long) is reported by name and is never silently renamed. [CT-1; corner: odd file names]

Acceptance:
- Given a 5 GB bundle and a piece size of 900 MB, when it is created, then every piece is at most 900 MB and the pieces add up to the whole.
- Given one damaged piece, when the bundle is checked, then that piece is named and no other piece is reported.
- Given a destination with too little space, when creation is asked, then nothing is written and the message states how much space is needed.

### FR7 Inside the air-gapped environment

- FR7.1 The tool checks that all pieces are present and undamaged, and names any piece that is missing or damaged. [Q6 A part]
- FR7.2 The tool puts the pieces back together into the original files, in a folder layout the web app can read; the layout is defined in the next design step. [Q6 B part]
- FR7.3 Each rebuilt file is checked against the manifest. A file that fails is not left in the output folder as if it were good. [CO-3]
- FR7.4 The tool lists the models available in a folder, showing for each its name, commit, capture date, size and licence name. [Q6 C]
- FR7.5 Pieces may arrive from several drives in any order; the tool tells the user which pieces are still missing. [Q5 B; Q1 of feasibility: drive sizes vary]
- FR7.6 The tool makes no network connection while doing FR7.1 to FR7.5. [request: air-gapped]

Acceptance:
- Given pieces copied from three drives in mixed order, when the check runs, then all are found and the whole verifies.
- Given the network switched off, when a bundle is rebuilt, then it completes without any error about the network.
- Given a rebuilt file that fails its checksum, when the rebuild ends, then the file is not present in the output folder and the run reports it.

### FR8 Installing and running

- FR8.1 The tool is delivered as one ready-to-run program file for Linux and one for Windows, so it can be brought into the air-gapped environment where Python is not installed. [Q7 B; feasibility Q3]
- FR8.2 The same commands behave the same way on both systems, and on both sides of the gap. [request; feasibility Q3]
- FR8.3 The tool reports its own version. [R4 in `raid-log.md`]
- FR8.4 On the internet side, the tool can also be installed with standard Python tools. [request: easily installed; Python skills in feasibility Q7]

Acceptance:
- Given a Windows computer without Python, when the program file is run, then the version command works.
- Given a Linux computer without Python, when the program file is run, then the version command works.

### FR9 Messages and records

- FR9.1 When anything fails, the tool names the file or step that failed and the reason, and ends with a non-zero status. A run that completes fully ends with status zero. [corner: error handling]
- FR9.2 The tool writes a run record listing what was fetched, skipped and failed, kept with the bundle. [CO-3 approval step needs to see what is being brought in]

Acceptance:
- Given a run with one failed file, when it ends, then the status is non-zero and the record names that file.

## Non-Functional Requirements

- NFR1 Download speed: on the user's own connection, downloading a large file reaches at least 80% of the connection's measured speed. How the connection's speed is measured is defined in the test plan (see assumption A3). [Q9, Q11 B; replaces the goal in `intent-statement` that had no number]
- NFR2 Integrity: a change of a single byte in any piece, any fetched file, or the manifest is detected by the check commands. Measured by a test that changes one byte at a time. [CO-3; FR5.4, FR6.5, FR7.3]
- NFR3 Restart: stopping the tool at any moment during download, bundling or rebuilding and running it again produces a correct, complete result, with no half-finished piece or file treated as complete. [FR5.3, FR6.6; corner: killed mid-work]
- NFR4 Damage isolation: replacing one damaged piece never requires copying any other piece again. [CO-2; FR6.5]
- NFR5 Offline: the commands used inside the air-gapped environment make zero network connections. Measured with the network blocked. [FR7.6]
- NFR6 Secrets: an access token supplied by the user never appears in a bundle, run record or message. [Construction phase guardrail on credentials; `team-practices` code style; corner: secrets]
- NFR7 Both systems: all automated tests pass on Linux and on Windows before a change is accepted. [`team-practices`; plan includes a Linux and Windows check step]
- NFR8 Testability: every requirement above has an automated test, written first. [`team-practices`: test-driven; every change has a test and existing tests stay green]

## Constraints

- All constraints in `constraint-register.md` stay in force, with this change: **the one-month deadline (CO-4) is not fixed**; Q12 says the date can move instead of dropping scope.
- Official libraries or the official command-line tool only, no scraping (CT-4). The older fast-transfer add-on is retired (CT-6).
- Hugging Face request limits apply to anonymous use (CT-8).
- Python is the builder's language (CO-6); Python 3.10 or newer on the internet side (CT-5).
- Changes follow `team-practices`: trunk-based, test-driven, `ruff` with line length 100.
- The remote repository is `https://github.com/jax79sg/ModelHub`; where automated checks run is not decided.

## Assumptions

- A1 Linux and Windows computers use 64-bit Intel/AMD processors; you did not name an architecture. [assumption]
- A2 The program file for each operating system can be built from the same code, each built on its own system; this is not yet tested. [assumption]
- A3 The connection's speed is measured by timing a large reference download on the same computer and connection, taken as the highest rate reached. [assumption]
- A4 Community discussions are not part of the first version because Q3 did not select them. [assumption]
- A5 In a run over many models, one type selection for the whole run is acceptable; you answered Q2 (both ways) and Q10 (stop and show) without saying how these combine. [assumption]
- A6 The README and small settings files must always be fetched, because the web app cannot show a model page without them. [assumption]
- A7 Resuming after an interruption is required for models this large; you did not state it directly. [assumption]
- A8 Hugging Face keeps anonymous reads of public models available (A5 in `raid-log.md`). [assumption]
- A9 The scan and approval step is done by other people on what is handed over; the tool only supplies the safety-scan data in FR3.3 to support it. [assumption]

## Out Of Scope

- Private and gated models, datasets and Spaces, and building or running the air-gapped web app itself, as in `intent-statement`.
- Running or hosting the web app, defining how it looks, and the exact folder layout it reads (settled in the next design step).

## Open Questions

- Which processor architectures must be supported (A1).
- The smallest piece size the tool accepts, and the size limit for README pictures (FR6.4, FR4.4); both are set in design.
- Where the automated checks run (open from `team-practices`); the later check-setup step must settle this.
- How "measured connection speed" is turned into a repeatable test (A3).

## Traceability

| Requirement | Traces to |
|-------------|-----------|
| FR1, FR2 | Q1, Q2, Q10; `intent-statement` scope; CO-3 |
| FR3 | Q3; success metric 1 in `intent-statement`; CR-2 |
| FR4 | Q4; success metric 1; R7 and R8 in `raid-log.md` |
| FR5, NFR1 | Q9, Q11; success metric 2 in `intent-statement`; E7 and E8; CT-6 |
| FR6, NFR3, NFR4 | Q5; feasibility Q1 and Q9; CO-1 and CO-2; R2 |
| FR7, NFR5 | Q5, Q6; request (air-gapped); CT-2 |
| FR8 | Q7; feasibility Q3; R3 |
| FR9, NFR2, NFR6 | CO-3; `raid-log.md`; phase guardrails |
| NFR7, NFR8 | `team-practices` |
