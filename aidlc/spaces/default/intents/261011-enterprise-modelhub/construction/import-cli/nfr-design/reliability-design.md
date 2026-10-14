# Reliability Design: import-cli

How a stopped run resumes.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR4.2 | Resume by design | Every request is safe to repeat; an interrupt stops sending and leaves the import on the service; a rerun creates again and gets the missing pieces. |
| NFR4.3 | One retry helper | Five retries at 1, 2, 4, 8 and 16 seconds plus up to 1 second of random wait for network errors, timeouts and retryable service errors; other errors fail the model at once. |
| NFR4.4 | Busy loop | On service_busy the command waits and asks every 60 seconds for up to 30 minutes (settings), shows 'waiting for a free place', then fails the model. |
| NFR3.1 | No availability design | The command runs when the person runs it. |
| NFR10.1 | Platform-neutral code | Pathlib for paths, no shell, no signals other than the interrupt, file permissions handled per platform; the import tests run on Linux, Windows and macOS. |
