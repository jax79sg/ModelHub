# Scalability Design: catalog

Sizing for one copy, 20 people at once and about 10,000 versions.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR7.2 | Database sizing | A 100 GB volume holds about 50 GB of documents plus records and indexes with 100% headroom; documents are at most 16 MiB; a check on the volume's free space is in the ready answer as a warning below 20%. |
| NFR7.3 | Connection pool of 10 | Twenty people and two imports need far fewer than 10 simultaneous queries; a request waits at most 5 seconds for a connection, else 503. |
| NFR7.4 | Stateless service | No state outside the database; a second copy would work unchanged, but only one runs. |
| NFR7.5 | Per-version limits | At most 10,000 files, 1,000 documents and 64 MiB of documents per version, enforced as a 422 before the store starts. |
