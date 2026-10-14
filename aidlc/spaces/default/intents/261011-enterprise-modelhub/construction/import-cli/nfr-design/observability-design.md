# Observability Design: import-cli

What the person and the run record show.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR6.1 | Progress display | On a terminal an updating line on standard error after 2 seconds (step, bytes, speed, time left); when not a terminal, one plain line every 10 seconds. |
| NFR6.2 | Report and exit status | One line per model and the counts; exit 0, 1 or 2 as designed. |
| NFR6.3 | Run record | The existing run record gets one line per model with result and code; the token is filtered out. |
