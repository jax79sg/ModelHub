# Scalability Requirements: import-cli

Size limits the command must handle.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR7.3 | Bundles up to 200 GB (up to 999,999 pieces by the format) are handled. | Progress and memory do not grow with the number of pieces | NFR7 |
| NFR7.4 | Lists of models are imported one after another. | A list of 50 bundles runs with constant memory | NFR7, rule BR1.11 |
