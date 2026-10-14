# Observability Design: artifactory-stand-in

What a test and an operator can read.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR6.1 | Shared log shape | Logs use the common log fields as JSON lines on standard output when run on its own; inside a test run they go to the test's log capture. |
| NFR6.2 | Recorded calls readable over a test-only control address | A separate path prefix, answered only to the test token, returns the recorded calls and clears them; it is not part of the imitated surface. |
| NFR6.3 | Register and checklist as data files | The assumption register is one data file; the checklist is produced from the entries needing confirmation; a test lists every answer the stand-in can give and fails if one has no register entry (rule BR1.13). |
