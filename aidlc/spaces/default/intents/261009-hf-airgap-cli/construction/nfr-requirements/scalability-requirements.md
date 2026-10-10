# Scalability Requirements

Derived from `requirements.md` (NFR1 and NFR4) and your answers in `nfr-requirements-questions.md` (Q8, Q9). This is a tool run by one person, not a service, so scale means how much data and how many items it can handle, not how many users.

## Load Projections

- Models in the air-gapped store: up to about 1,000 (Q8 C).
- Versions kept per model: up to about 10 (Q9 C), so up to about 10,000 version folders.
- Model size: many models, some over 100 GB (feasibility Q5 C); the planning ceiling for a single file is 1 TB (assumption).
- Smallest transfer drive: under 1 GB (feasibility Q9), so a very large file needs very many pieces.

## Requirements

| ID | Requirement | Pass criterion | Source |
|----|-------------|----------------|--------|
| NFR1.9 | A single file of at least 1 TB can be downloaded, bundled, verified and rebuilt without running out of memory (see NFR1.3) | A generated 1 TB sparse test file goes through bundle, verify and unpack within the 8 GB memory limit | Feasibility Q5; planning ceiling (assumption) |
| NFR1.10 | A bundle can have up to 999,999 pieces; the piece numbering in `contract-summary.md` (six digits) supports this | A test bundle of 1,000,000 pieces is refused with a message, and 999,999 pieces are accepted | Contract C2 |
| NFR1.11 | The store can hold at least 10,000 version folders without a change in layout or in the cost of working on one bundle | See NFR1.7 and NFR1.8 in `performance-requirements.md` | Q8, Q9 |
| NFR4.4 | The number of piece-by-piece checks scales with the damaged pieces, not the whole bundle: after a first full check, re-checking only replaced pieces reads only those pieces | A re-check after replacing 1 of 10,000 pieces reads about 1/10,000 of the bytes | Requirements NFR4 |

## Scaling Strategy

- There is nothing to add or remove at run time. Scaling is by streaming in blocks (NFR1.4), by working on one model at a time, and by keeping each version in its own folder.
- The one tunable is how many files download at once (NFR1.2).

## Growth And Capacity

- Disk space is the real limit. The tool checks free space before writing (FR6.7) and states how much it needs. A store of 1,000 models of 100 GB each would need about 100 TB; this is your planning concern, not a tool limit.
- Each version of a model is stored in full. Sharing identical files between versions is not in the first version (hypothesis: worth adding if disk space becomes the limit).
