# Scalability Design: import-cli

Handling many pieces and long lists with constant memory.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR7.4 | Bounded run state | A run holds the current package and the report entries; a list of 50 bundles uses the same memory as one. |
