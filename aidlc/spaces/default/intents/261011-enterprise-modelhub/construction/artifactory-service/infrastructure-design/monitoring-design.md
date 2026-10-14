# Monitoring Design: artifactory-service

Metrics come from this service's logs and ready check; the existing central monitoring routes the alerts.

## Metrics And KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| Ready check status | GET /readyz | 503 over 5 minutes in business hours | The service cannot serve |
| Import outcomes | events import_done, import_failed, import_skipped | Any failed as interrupted or artifactory_inconsistent | Needs a person |
| Import duration for 100 GB | import_done event with bytes and times | Over 4 hours on a 1 Gbit/s link | The target of NFR7.1 |
| Working volume free space | ready answer | Under 25% free | A large import could be refused (507) |
| Artifactory reachability | ready answer | Down over 10 minutes | Imports and removals fail |
| Catalog reachability | ready answer | Down over 10 minutes | Imports cannot be recorded |
| Request error share | 5xx access lines | Over 5% for 10 minutes | Users see failures |

## Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| Service not ready | Ready 503 over 5 minutes in business hours | High | Central monitoring |
| Import failed needing a person | interrupted or artifactory_inconsistent | Medium | Central monitoring |
| Working volume low | Under 25% free | Medium | Central monitoring |
| Artifactory or Catalog down | Down over 10 minutes | High | Central monitoring |
| High error share | 5xx over 5% for 10 minutes | Medium | Central monitoring |

## SLIs And SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| Imports that end done, skipped or fail with a clear reason (none lost or stuck) | 100% | Every import |
| Short calls (create, progress, lists) under 1 second | At least 95% | Rolling 30 days |
| 100 GB import end to end | Under 4 hours on a 1 Gbit/s link | Measured when a real Artifactory is available |

## Logs And Tracing

JSON lines on standard output to the existing central logging: an access line per request and a line per import state change (import id, model, step, bytes), with fixed event codes. The Artifactory tool's raw output is logged only after redaction. The request id given by the CLI or the portal appears on every line, which gives tracing across the CLI, this service and the Catalog. Dashboard: ready status, running imports, import outcomes, bytes per hour, working volume space, Artifactory and Catalog reachability.
