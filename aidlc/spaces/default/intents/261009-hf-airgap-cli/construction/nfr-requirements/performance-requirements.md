# Performance Requirements

Derived from `requirements.md` (NFR1) and your answers in `nfr-requirements-questions.md` (Q1, Q2, Q8, Q9). NFR1 is the performance family: speed, memory, progress and scale. Every row keeps its inception ID with a sub-number. Contract references (C1 to C4) are in `contract-summary.md`. There is no `functional-spec` or `rules` document because the logic-design step was skipped by the approved plan.

## Requirements

| ID | Requirement | Pass criterion | Source |
|----|-------------|----------------|--------|
| NFR1.1 | Downloading a large file reaches at least 80% of the connection's measured speed | On the user's connection, tool throughput is at least 0.8 times a reference download of a large public file timed with a plain single-connection range request taken as the connection's best rate (see assumption A3 in `requirements.md`) | Requirements Q9, Q11 |
| NFR1.2 | Several files are fetched at the same time; the default is 8, and the user can change it | With a model of at least 8 files, 8 transfers are active at once by default | Requirements FR5.2; `feasibility-assessment.md` E11 |
| NFR1.3 | Memory use stays at or below 8 GB at its peak in any step, for any file size | Processing a 500 GB test file keeps resident memory at or below 8 GB, measured with a resource limit | NFR questions Q1 |
| NFR1.4 | Checksums and archive steps read files in blocks, never whole files | A test that sets a 256 MB memory limit while checking a 2 GB file passes | NFR1.3 |
| NFR1.5 | Any step that takes longer than 2 seconds shows live progress: the current item, bytes done of total, rate, and estimated time left | On a terminal the display changes at least every 2 seconds; when output is not a terminal, a progress line is written at least every 30 seconds | NFR questions Q2 ("so people don't think it hung") |
| NFR1.6 | Putting a 100 GB model back together and checking it has no time limit, provided it can be stopped and restarted (see NFR3.1) | A stopped rebuild resumes (NFR3.4); no timeout ends it | NFR questions Q2 D |
| NFR1.7 | `list` on a store of up to 1,000 models with up to 10 versions each (10,000 version folders) finishes within 5 seconds on a local disk | A test store of 10,000 version folders is listed in at most 5 seconds | NFR questions Q8 C, Q9 C |
| NFR1.8 | Time to verify or rebuild one bundle depends only on the size of that bundle, not on how many models are already in the store | Verifying the same bundle against an empty store and against the 10,000-folder store differs by no more than 10% | NFR questions Q8, Q9 |

## Notes

- Targets with a number that came from me, not from you, are design defaults: the 2-second and 30-second progress intervals, the 5-second `list` time, and the 10% difference. They are marked as assumptions in `raid-log.md` terms and can be changed.
- NFR1.1 can only be measured on a real connection, so it is a benchmark run by hand or on a schedule, not part of the quick automated tests (see NFR8.2 in `reliability-requirements.md`).
