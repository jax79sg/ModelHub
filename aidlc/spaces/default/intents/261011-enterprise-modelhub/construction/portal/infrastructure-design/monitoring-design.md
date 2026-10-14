# Monitoring Design: portal

Metrics come from the portal's logs and ready check; the existing central monitoring routes the alerts.

## Metrics And KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| Ready check status | GET /readyz | 503 over 5 minutes in business hours | People cannot use the portal |
| Page latency | duration field of page lines | 95th percentile over 800 ms for 10 minutes | Below the 1-second target (NFR2.1) |
| Error share | 5xx lines | Over 5% for 10 minutes | People see failures |
| Sign-in failures | events sign_in_failed | More than 20 in 10 minutes | Keycloak or client problem |
| Catalog or Keycloak unreachable | ready answer | Down over 10 minutes | Pages show service-down messages |

## Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| Portal not ready | Ready 503 over 5 minutes in business hours | High | Central monitoring |
| Slow pages | p95 over 800 ms for 10 minutes | Medium | Central monitoring |
| High error share | 5xx over 5% for 10 minutes | Medium | Central monitoring |
| Sign-in failing | More than 20 sign-in failures in 10 minutes | Medium | Central monitoring |

## SLIs And SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| Models list page in under 1 second | At least 95% | Rolling 30 days, measured on the server |
| Non-5xx page responses | At least 99% in business hours | Rolling 30 days |

## Logs And Tracing

JSON lines on standard output to the existing central logging, one access line per request with request id, user name, path, status and duration, plus events sign_in, sign_in_failed, sign_out, token_made and retention_decided. Tokens, cookies and form tokens are never logged. The request id is passed to the Catalog and artifactory-service, giving tracing across the three. Dashboard: ready status, request rate, latency percentiles, 5xx share, sign-ins.
