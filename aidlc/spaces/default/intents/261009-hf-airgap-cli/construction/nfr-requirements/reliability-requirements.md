# Reliability Requirements

Derived from `requirements.md` (NFR3, NFR4, NFR7, NFR8) and `contract-summary.md`. Availability targets such as "99.9% uptime" do not apply to a command-line tool. Reliability here means: it can be stopped at any time, a damaged copy never passes as good, and it behaves the same on both systems.

## Fault Tolerance And Restart

| ID | Requirement | Pass criterion | Source |
|----|-------------|----------------|--------|
| NFR3.1 | Stopping the tool at any moment (power loss, closed window, Ctrl-C) and running it again gives a correct, complete result. A half-written file or piece never looks finished | A test stops the tool at every write point in turn; the re-run succeeds and `verify` passes | Requirements NFR3 |
| NFR3.2 | A restarted download does not fetch again any file already checked as complete | After stopping half-way, the re-run fetches only the missing files | Requirements FR5.3 |
| NFR3.3 | A restarted `bundle` does not rewrite a piece already written and checked | The re-run leaves the earlier pieces' modification times unchanged | Requirements NFR3 |
| NFR3.4 | A restarted `unpack` continues from the files already rebuilt and checked | The re-run rebuilds only the remaining files | Requirements NFR3; NFR questions Q2 D |
| NFR3.5 | A network error is retried up to 5 times per file, waiting 1, 2, 4, 8 and 16 seconds, each with a small random extra wait. After that the file is marked failed and the run continues | A simulated server that fails 5 times then succeeds is retried; one that always fails ends that file as failed | Design default from `nfr-design-patterns.md` (assumption) |
| NFR3.6 | If the destination fills up or a drive is removed during a write, the tool stops with a message naming the piece. Only that piece is written again after the problem is fixed | A test that fails the write of piece 7 leaves pieces 1 to 6 untouched and reports piece 7 | Requirements FR6.7 |
| NFR3.7 | Two runs on the same output folder at the same time are not allowed: the second stops with a message | Starting a second run while one holds the folder ends with status 2 | Corner checklist (concurrency) |
| NFR3.8 | The free-space check is made before writing | See FR6.7 in `requirements.md` | Requirements FR6.7 |
| NFR4.1 | Replacing one damaged piece never requires copying another piece again | After replacing one piece, `verify` passes without touching others | Requirements NFR4 |
| NFR4.2 | One `verify` run lists every missing or damaged piece, not only the first | A test bundle with 3 bad pieces gets all 3 reported in one run | Requirements NFR4 |
| NFR4.3 | Pieces can arrive in any order and from several drives; the tool lists what is still missing | See FR7.5 in `requirements.md` | Requirements FR7.5 |

## Platform Reliability

| ID | Requirement | Pass criterion | Source |
|----|-------------|----------------|--------|
| NFR7.1 | The Windows program runs on Windows 10, Windows 11 and Windows Server 2016 to 2022. The Linux program runs on Ubuntu 20.04 and RHEL 8 and on newer Linux. Both are 64-bit Intel/AMD | The version command and a bundle round trip pass on each listed system | NFR questions Q5 A-E, Q6 A-B |
| NFR7.2 | The Linux program is built on the oldest system it must run on, so it does not need a newer system library than that system has | The program starts on a RHEL 8-compatible system and on Ubuntu 20.04 | NFR questions Q5 E |
| NFR7.3 | All automated tests pass on Linux and on Windows before a change is accepted | The check pipeline runs the tests on both and blocks a change when either fails | Requirements NFR7; `team-practices` |
| NFR7.4 | Files the tool writes are UTF-8. A byte-order mark or Windows line endings in a README are read correctly and kept as found | A test README with a mark and Windows line endings round-trips unchanged | Corner checklist (formats) |
| NFR7.5 | Path rules of both systems are respected: names that Windows cannot hold are reported, never silently changed, and long paths work | A test repository with a name reserved on Windows and a 300-character path is handled as FR6.8 says | Requirements FR6.8 |
| NFR7.6 | Two model names that differ only by letter case are detected before writing on a case-insensitive system, and the run stops for that model with a message | A pair of names such as `Org/Model` and `org/model` triggers the message on Windows | Open question in `contract-summary.md` |

## Test Reliability

| ID | Requirement | Pass criterion | Source |
|----|-------------|----------------|--------|
| NFR8.1 | Every requirement has an automated test, written before the code | Each requirement row in these documents has a named test, written first | `team-practices` (test-driven) |
| NFR8.2 | The normal test suite needs no internet. It uses saved copies of Hugging Face responses. A small set of tests that use the real network is marked and run only on request | Running the suite with the network blocked passes, except the marked set | Requirements NFR8; practical need for repeatable checks |

## Graceful Degradation

- If Hugging Face is unavailable, `pull` fails with a clear message and leaves resumable state. Every other command works.
- If a README picture cannot be fetched, the model still completes and the picture is listed as failed (FR4.3).
- If a model is private or gated, only that model fails (FR1.4).
- If the signature check fails, nothing is rebuilt (NFR2.4). This is deliberate: it fails closed.
