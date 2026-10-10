# Observability Requirements

Derived from `requirements.md` (FR9, NFR2, NFR3, NFR8) and your answers in `nfr-requirements-questions.md` (Q2). A command-line tool has no dashboards or alerts. Observability here means: the person running it can see what is happening, and afterwards can prove what happened.

## Logging And Messages

| ID | Requirement | Pass criterion | Source |
|----|-------------|----------------|--------|
| NFR8.3 | The run record (`run-record.json`) lists every item fetched, skipped and failed, with sizes, timings, retry counts, the tool version and the platform. Its layout carries a format version | A test run's record validates against its published layout and lists every item | Requirements FR9.2 |
| NFR8.4 | Three levels of detail: normal (progress and errors), verbose, and debug. Verbose and debug are written to a log file beside the output, with times in UTC. Nothing at any level contains a secret (see NFR6.1) | The three levels produce increasing detail; a search of all logs for a fake token finds nothing | Corner checklist (time; secrets) |
| NFR8.5 | Exit status follows contract C4: 0 for complete success, 1 when at least one item failed, 2 when the command could not run | Each status is produced by a test | `contract-summary.md` C4 |
| NFR1.5 | Live progress for long steps (current item, bytes, rate, time left) | See `performance-requirements.md` | NFR questions Q2 |
| NFR2.10 | An integrity failure names the piece or file and the check that failed | A damaged test piece is named in the output and in the run record | Requirements FR9.1 |

## Metrics And Health

- There is no running service to monitor. The measures that matter are in the run record: bytes moved, time taken per item, retries, and failures.
- A repeatable download-speed benchmark (NFR1.1) is kept as a separate script and its results are saved with date, model, computer and link speed, so a slowdown after a change can be seen.

## Service Level Indicators

Not applicable in the usual sense (no uptime). Two measures stand in for them:

- Speed ratio: measured throughput divided by the connection's reference rate, target at least 0.8 (NFR1.1).
- Integrity pass rate: share of pieces and files that verify on first check, target 100% for correctly made bundles (NFR2.1).

## Alerting

None. Failures are shown on screen and in the exit status; there is nothing to page.

## Dashboards

None required. The run record is the source for any report you later want to build.
