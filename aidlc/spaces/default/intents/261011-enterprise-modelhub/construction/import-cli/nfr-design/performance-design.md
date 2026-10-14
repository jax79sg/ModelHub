# Performance Design: import-cli

How the command sends large bundles within memory and uses the link.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR7.1, NFR7.3 | Block reads, constant memory | Pieces are read and hashed in blocks of at most 8 MiB and sent as a stream; progress counters are the only state that grows, and they do not grow with the number of pieces. |
| NFR7.2 | One piece at a time over a kept-alive connection | A single connection is reused for the whole run; sending is not paused between pieces beyond the checksum header; throughput is limited by the link. |
| NFR1.1 | Poll every 2 seconds and print at once | Progress is asked every 2 seconds and the final report is printed when the service says done. |
| NFR4.1 | Send only missing pieces | The create answer lists missing pieces; the command sends exactly those. |
