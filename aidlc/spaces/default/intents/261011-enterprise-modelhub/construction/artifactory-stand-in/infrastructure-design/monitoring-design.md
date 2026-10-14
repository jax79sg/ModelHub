# Monitoring Design: artifactory-stand-in

There is nothing to monitor in production. What a test can read is listed so the build shows problems.

## Metrics And KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| Startup time | Test fixture timer | Over 2 seconds fails a test | Keeps the test suite fast (NFR9.1) |
| Call count by status | Call record | Read by the test | Lets a test assert what the system did |
| Assumption coverage | Register test | Any answer without an entry fails the build | Keeps the checklist complete (FR7.2) |

## Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| Stand-in test failure | Any stand-in test fails in CI | High: blocks merge | Pull-request checks |
| Stand-in found in a delivered file | Image or program check finds it | Critical: blocks release | Release workflow |

## SLIs And SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| Stand-in test suite passes on all CI systems | 100% on every merge | Per pull request |

## Logs And Tracing

Logs go to the test's log capture in the shared log shape. No aggregation or tracing is needed. The call record and the failure-switch state are readable through the test-only control address while the test runs.
