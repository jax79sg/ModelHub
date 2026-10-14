# Performance Design: artifactory-service

How the service keeps up with the link and stays within memory while handling bundles up to 200 GB.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR7.1, NFR7.2 | Streaming pipeline with bounded blocks | Pieces are written to disk while their checksum is computed in 8 MiB blocks; unpacking reads pieces in order in 8 MiB blocks and writes files while hashing them; a consumed piece is deleted at once. Nothing is read whole into memory. The service's own work therefore runs at disk speed, and the 100 GB in 4 hours target (about 7 MB/s) is dominated by the links. |
| NFR7.3 | Fixed block size and no whole-file reads | All reads and writes use blocks of at most 8 MiB; a test with a declared 200 GB piece set watches memory. |
| NFR1.1 | Record sent immediately after the listing matches | No wait states between the upload check and the Catalog call. |
| NFR2.1 | Short calls do no heavy work | Create reads the signed description and does one listing and one Catalog lookup; progress reads the job row; key and retention lists read small tables; the Artifactory listing has a 30-second read limit. |
| NFR4.1 | Piece acknowledgement after one move | A piece is acknowledged after its temporary file is renamed into place and its row written; no other work happens on that call. |
