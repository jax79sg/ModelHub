# Performance Design: artifactory-stand-in

How the stand-in meets its small speed and size targets.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR9.1, NFR9.5 | In-process server on a free port | FastAPI and uvicorn start in a thread of the test run; the port is picked by the operating system; startup does no disk scan and no network setup, so the first answer is ready in well under 2 seconds. |
| NFR9.2 | State in memory, content on disk only when kept | Version and file records are plain in-memory tables; only kept file content touches the temporary folder; answers that move no content never wait on disk. |
| NFR9.3 | Virtual files streamed through a checksum, then dropped | A file above the keep limit is read in blocks of 64 KiB into a SHA-256 and discarded; nothing but name, size and checksum is held, so a declared 1 TiB file costs a few kilobytes. |
