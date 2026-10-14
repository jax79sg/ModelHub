# Scalability Requirements: catalog

Sized for one server and one copy of the service.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR7.1 | Sized for about 1,000 models and up to 10 versions each (10,000 versions). | All NFR2 targets hold at that size | NFR7 |
| NFR7.2 | Planned database size. | Plan for 100 GB: about 50 GB of documents (average 5 MB per version) with 100% headroom; documents are at most 16 MiB each | NFR7, FDQ3 A |
| NFR7.3 | Concurrency. | 20 people at once plus up to 2 imports recording; a pool of 10 database connections | NFR7, NFR questions Q2 A |
| NFR7.4 | One copy of the service; no sticky state outside the database. | A second copy could be started without change, but is not required | NFR7 |
| NFR7.5 | Per-version limits. | At most 10,000 files, 1,000 documents and 64 MiB of documents per stored version; larger is refused with 422 | NFR7, rule BR1.4 |
