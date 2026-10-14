# Performance Design: catalog

How the Catalog meets its speed targets without a cache (NFR design question 1 A).

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR2.1, NFR7.1 | Narrow summary table with one index per filter and sort | The models list reads only the ModelSummary table; each filter (task, library, licence, language, parameter band, importer, import time) and each sort field has an index; null values sort last through the index order; pages use keyset-friendly ordering with a tie-break on model id. No cache is used (question 1 A). |
| NFR2.2 | Documents in a separate table the list never joins | The documents table is reached only by the document and version-record routes; a test counts tables read by the list. |
| NFR2.3 | Stored search vector with a GIN index, plus trigram indexes on id and tags | The card text is turned into a search vector when stored; whole-word English matching uses the vector index, and parts-of-word matching on model ids and tags uses a trigram index; both are updated in the store transaction. |
| NFR2.4 | Version record without documents | The version route returns the record, files and document names only, with one query for files; documents are separate calls. |
| NFR2.5 | Documents as a binary column read in one piece (question 2 A) | A document up to 16 MiB is read from its own row and sent with the headers of rule BR1.11; first byte is available as soon as the row is read. |
| NFR1.1 | Summary row written in the store transaction | The model is visible in the list when its store commits; no index rebuild or delayed job. |
| NFR4.1 | One transaction, batched inserts | Files and refs are inserted in batches inside the store transaction; document content is written once; the identical-repeat check compares one stored checksum before any write. |
| NFR2.6 | Query time limit | Each connection sets a 5-second statement limit; a cancelled query is answered with 503 and logged. |
