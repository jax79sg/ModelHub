# Rules: import-cli

The decisions the CLI makes when importing. Sources are requirement, contract and decision IDs and the answers in `functional-design-questions.md` (FDQ). Error codes are those of contract C1.

```yaml
unit: import-cli
rules:
  - id: BR1.1
    statement: The server address and token are saved only by login, in a file only the person can read, and cannot be given on the command line.
    category: policy
    applies_to: [ClientSettings]
    trigger: login; logout; any import
    logic: "login asks for the server address and the token (the token typed with no echo, or read from standard input when it is not a terminal). The address must be https, except localhost and 127.0.0.1 where http is allowed. The file lives in the person's own settings folder (Linux: ~/.config/modelhub; Windows: the person's own application data folder) with permissions only for that person (Linux mode 600); IF the permission cannot be set THEN nothing is saved and login stops with an error. logout deletes the file. MODELHUB_SERVER and MODELHUB_TOKEN, when set, override the file for that run. There is no --token option; an attempt to pass one is an error that points at login."
    violation: login stops; exit status 2
    source: [FR1.2, FR1.11, FDQ2 A]
  - id: BR1.2
    statement: The token and anything derived from it never appear in output, logs, the report, error messages or the run record.
    category: policy
    applies_to: [ClientSettings, ModelReportEntry]
    trigger: any output
    logic: "Every line printed or logged is passed through a filter that replaces the token's value and the Authorization header with [redacted]. Server messages are shown as received only after the same filter. The settings file's path may be shown; its contents may not."
    violation: not applicable
    source: [FR1.11, NFR5b]
  - id: BR1.3
    statement: Without settings, or with a token the service refuses, the CLI cannot run at all and says how to fix it.
    category: validation
    applies_to: [ClientSettings, RunReport]
    trigger: start of import; first service answer
    logic: "IF no server or token is available THEN print 'run modelhub login' and exit with status 2 before reading any bundle. IF the service answers 401 token_invalid THEN stop the whole run (not model by model) with its message, which says to make a new token in the portal when the token is revoked or expired, and exit with status 2."
    violation: exit status 2
    source: [FR1.2, FR1.10, AC4.3]
  - id: BR1.4
    statement: Each bundle is verified on the import computer before anything is sent; one that fails is reported and the others carry on.
    category: validation
    applies_to: [ImportPackage]
    trigger: each bundle given to import
    logic: "A bundle is named by its description file (.bundle.json), its first piece, or a folder (searched one level deep for .bundle.json files). Check it with the existing verify code: the signature is by a key trusted on this computer and every piece matches the signed description. The result (counts of pieces and bytes checked, key fingerprint, time) becomes check_results. A bundle that fails is reported as failed with the existing verify message and the run continues. Nothing is sent for it."
    violation: failed entry in the report
    source: [FR1.1, FR1.2, C8]
  - id: BR1.5
    statement: A verified package is sent as create, missing pieces one at a time in order, start, then watched until the service ends it.
    category: policy
    applies_to: [Transfer, ImportPackage]
    trigger: each verified package
    logic: "Create the import with the description, signature, model id, commit, bundle name, this computer's name, the tool version and check_results. IF the service answers 200 skipped THEN the entry is skipped and nothing is sent. IF 201 THEN send each missing piece in increasing index order, one request at a time, reading the file in blocks (never the whole piece in memory) and sending its SHA-256 in X-Piece-SHA256. Then call start and ask for progress every 2 seconds until the state is done, failed or skipped. The outcome of the service (imported, completed or failed) becomes the entry's result. A rerun sends only the pieces the service reports missing."
    violation: not applicable
    source: [FR1.1, FR1.4, FR1.5, FR1.6, C1, FDQ3 A]
  - id: BR1.6
    statement: Network errors and retryable service errors are retried five times with growing waits; errors that are not retryable fail the model at once.
    category: policy
    applies_to: [Transfer]
    trigger: any request that fails
    logic: "For a connection error, a timeout, a 5xx answer or an error with retryable true: wait 1, 2, 4, 8 and 16 seconds in turn, each with a random extra wait of up to 1 second, and send the same request again (every C1 request is safe to repeat). After the fifth retry fails, mark the model failed with the last reason and go on to the next. For an error with retryable false (including model_locked, name_rule_broken, untrusted_signing_key, bad_signature, artifactory_conflict, artifactory_inconsistent, manifest_mismatch, catalog_conflict): fail the model at once with the service's message. A piece_mismatch answer re-sends that piece once, then fails the model."
    violation: failed entry
    source: [FR1.9, FR1.12, AC1.8, AC1.9, C1]
  - id: BR1.7
    statement: When the service is busy, the CLI waits for a free place instead of failing at once.
    category: policy
    applies_to: [Transfer]
    trigger: service_busy answer on start
    logic: "Show 'waiting for a free place' and ask again every 60 seconds (setting busy_poll_seconds) for up to 30 minutes (setting busy_wait_minutes). IF still busy after that THEN fail the model with the reason 'the service stayed busy' and go on. While waiting, the pieces stay on the service."
    violation: failed entry
    source: [FR1.9, FDQ4 B, NFR7]
  - id: BR1.8
    statement: Stopping the program leaves the import to be resumed, and says so.
    category: constraint
    applies_to: [Transfer]
    trigger: interrupt (Ctrl-C) or crash during a transfer
    logic: "Stop sending at once, do not cancel the import on the service, print which models were not finished and that running the same command again resumes them, and exit with the existing tool's interrupt status."
    violation: not applicable
    source: [NFR4, existing behaviour]
  - id: BR1.9
    statement: The report lists each model as imported, skipped, completed or failed with its reason, and the exit status follows the results.
    category: policy
    applies_to: [ModelReportEntry, RunReport]
    trigger: end of run
    logic: "One line per model: model id, commit, result and, for failed, the reason and the service's code. Skipped says 'already imported'. Completed says whether 'files were already in Artifactory; record completed' or 'files uploaded again; record kept'. After the lines, the counts. Exit status: 0 when every model is imported, skipped or completed; 1 when at least one failed; 2 when the run could not start (BR1.3, a bad option, no bundle found, or a too-old program answer in BR1.14). A failed model never changes the others' results."
    violation: not applicable
    source: [FR1.10, FR1.11, AC1.2, AC1.3, existing C4]
  - id: BR1.10
    statement: Any step that takes more than 2 seconds shows live progress.
    category: policy
    applies_to: [Transfer]
    trigger: a step passes 2 seconds
    logic: "On a terminal show the step, bytes done and total, speed and time left on one updating line on standard error. When output is not a terminal, print one plain line every 10 seconds instead. Progress lines contain no token."
    violation: not applicable
    source: [FR1.13]
  - id: BR1.11
    statement: A list of models is imported one after another in the order given, and a failure does not stop the rest.
    category: policy
    applies_to: [RunReport]
    trigger: more than one package
    logic: "Process the packages one at a time, in the order given. A package that fails, is skipped or completes does not change the handling of the next."
    violation: not applicable
    source: [FR1, AC1.3]
  - id: BR1.12
    statement: Import behaves the same on Linux and Windows and needs nothing installed beyond the program.
    category: constraint
    applies_to: [ClientSettings, Transfer]
    trigger: any run
    logic: "Paths are handled with the platform's own rules; file names with spaces and non-ASCII characters work; no shell is started; the settings folder follows BR1.1; line endings and encodings in the report are the platform's. The import uses the program's own network library, so the single-file program and the offline packs need nothing else."
    violation: not applicable
    source: [NFR10]
  - id: BR1.13
    statement: The option for importing an old model-store folder is reserved, and until it is built it says so.
    category: policy
    applies_to: [RunReport]
    trigger: import --from-store
    logic: "Print 'importing an old model-store folder is not available in this version' and exit with status 2 without doing anything."
    violation: exit status 2
    source: [FR8, FR8.1, FDQ5 C]
  - id: BR1.14
    statement: The program tells the service its version, and a service that needs a newer program is obeyed.
    category: constraint
    applies_to: [RunReport]
    trigger: every request
    logic: "Send X-Modelhub-Client with the program's version. IF the service answers 426 THEN stop the run with its message and exit with status 2. The existing commands and their exit statuses are not changed by the import command."
    violation: exit status 2
    source: [C1 versioning, FR1.10]
```

## Rules Summary

| ID | Rule | Category |
|----|------|----------|
| BR1.1 | login saves settings privately | policy |
| BR1.2 | Token never shown | policy |
| BR1.3 | No settings or bad token: exit 2 | validation |
| BR1.4 | Verify locally first | validation |
| BR1.5 | Create, send, start, watch | policy |
| BR1.6 | Retries | policy |
| BR1.7 | Wait when busy | policy |
| BR1.8 | Interrupt leaves import resumable | constraint |
| BR1.9 | Report and exit status | policy |
| BR1.10 | Progress | policy |
| BR1.11 | List processed in order | policy |
| BR1.12 | Same on Linux and Windows | constraint |
| BR1.13 | --from-store reserved | policy |
| BR1.14 | Client version header; 426 | constraint |
