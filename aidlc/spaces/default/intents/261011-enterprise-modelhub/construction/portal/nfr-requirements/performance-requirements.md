# Performance Requirements: portal

Targets for the portal's pages, measured on the server with 20 people at once.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR2.1 | The models list page answers quickly end to end on the server. | At least 95 of 100 requests under 1 second at 1,000 models (the Catalog's own time included) | NFR2, NFR-AC1 |
| NFR2.2 | A model page without pictures renders quickly. | 95th percentile under 1 second | NFR2 |
| NFR2.3 | Page weight is small. | Under 300 KB per page without README pictures; script optional; no outside files | NFR2, rule BR1.17 |
| NFR2.4 | The sign-in redirect and callback add little time. | Under 500 ms on the portal's side | NFR2 |
| NFR1.1 | A model appears in the portal at once after the Catalog records it. | No portal cache; every page reads the Catalog | NFR1, rule BR1.11 |
| NFR7.1 | 20 people at once. | The targets above hold under that load | NFR7, NFR questions (catalog) Q2 A |
