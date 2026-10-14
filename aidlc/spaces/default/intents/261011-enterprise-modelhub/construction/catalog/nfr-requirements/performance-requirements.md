# Performance Requirements: catalog

Targets for the Catalog service. Load assumption: up to 20 people at once plus one or two imports (NFR questions Q2 A); data size as in the capacity table.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR2.1 | The models list, with any filters, sort and paging, answers quickly. | At least 95 of 100 requests under 1 second at 1,000 models and 10,000 versions, with 20 people at once, measured on the server | NFR2, NFR-AC1 |
| NFR2.2 | The list does not read stored documents. | A test counts the tables read; documents are never among them (rules BR1.8) | NFR2, rule BR1.8 |
| NFR2.3 | A text search answers as quickly as a plain list. | 95th percentile under 1 second for a search of one to three words | NFR2, rule BR1.9 |
| NFR2.4 | One model or version record (without documents) answers quickly. | 95th percentile under 300 ms | NFR2 |
| NFR2.5 | The first byte of a stored document arrives quickly. | Under 1 second for a document up to 16 MiB, streamed | NFR2 |
| NFR1.1 | A model is visible in the list the moment its store commits, because the summary row is written in the same transaction. | A test lists right after a store and finds it; no delayed index step | NFR1, rule BR1.7 |
| NFR4.1 | A first store of a version completes in reasonable time. | A version with 10,000 files and 100 MB of documents in under 60 seconds; an identical repeat in under 1 second | NFR4, rule BR1.2 |
| NFR2.6 | Database queries are limited so one slow query cannot hold the service. | 5-second limit per query; longer ones are cancelled and answered with 503 | NFR2 |
