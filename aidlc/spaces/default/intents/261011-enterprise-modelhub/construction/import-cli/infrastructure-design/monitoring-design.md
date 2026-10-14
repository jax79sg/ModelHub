# Monitoring Design: import-cli

The program runs on people's computers, so there is no central monitoring of it. What matters is what the person sees and what the service sees of the call.

## Metrics And KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| Exit status of a run | The program | 1 or 2 means a person must look | Shown to the person; scripts can act on it |
| Run record lines | Existing run record | Failed entries | Support can read what happened without secrets |
| Service-side view of the call | artifactory-service logs (request id, person, import id) | Failed or interrupted imports | Operators can match a complaint to an import |

## Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| Many imports failing for a person | Repeated import_failed for one person in the service logs | Low | Central monitoring, as it routes |

## SLIs And SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| Imports that end with a clear result and exit status | 100% | Every run |

## Logs And Tracing

The existing run record keeps one line per model with result and code, with the token filtered out. The request id of each call is shown in failure messages so an operator can find the service-side log lines.
