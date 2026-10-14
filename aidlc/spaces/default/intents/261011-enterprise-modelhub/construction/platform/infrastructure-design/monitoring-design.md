# Monitoring Design: platform

The existing central monitoring and logging are outside the containers. This document says what they must collect and poll for the whole stack, and what the host itself must be watched for.

## Metrics And KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| Container health | Docker health checks and /readyz of each service | Any unhealthy over 5 minutes in business hours | A part of the stack is down (NFR3.1) |
| Host disk free: database volume | Host monitoring | Under 20% | NFR7.2 |
| Host disk free: import-work volume | Host monitoring and the service's ready answer | Under 25% | Large imports would be refused |
| Host memory and CPU | Host monitoring | Memory over 90% for 10 minutes | Containers may be killed |
| Certificate expiry | Proxy / host monitoring | Under 30 days | People would lose access |
| Proxy error share | Proxy access log 5xx | Over 5% for 10 minutes | Entry point trouble |

## Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| Stack unhealthy | Any container unhealthy over 5 minutes in business hours | High | Central monitoring |
| Volume nearly full | Database under 20% or working volume under 25% free | Medium | Central monitoring |
| Certificate expiring | Under 30 days | Medium | Central monitoring |
| Host memory high | Over 90% for 10 minutes | Medium | Central monitoring |
| Proxy errors | 5xx over 5% for 10 minutes | Medium | Central monitoring |

## SLIs And SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| Stack healthy in business hours | No promised percentage (NFR3); back within 4 business hours of a failure noticed | Per incident |
| Upgrade and return rehearsal passes | Yes, once before first use, and for each major release | Per release |

## Logs And Tracing

Every container writes JSON lines to standard output; Docker's log driver passes them to the host, where the existing central logging collects them. Log rotation on the host keeps them from filling the disk. The request id set by the proxy (or taken from the caller) is carried through portal, artifactory-service and Catalog, which gives tracing across the stack. Dashboards are built by the monitoring team from the metrics above.
