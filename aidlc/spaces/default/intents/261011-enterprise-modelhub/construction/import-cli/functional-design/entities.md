# Entities: import-cli

Inputs: `unit-of-work.md` (U6), `components.md` (SignIn, PackageSource, ImportClient), `requirements.md` (FR1, FR1.2, FR1.9 to FR1.11, FR1.13, FR8, NFR10), contract C1 and the existing bundle format C8, and the answers in `functional-design-questions.md` (written FDQ). The CLI keeps no database. Its only stored thing is the settings file; the rest is held for the length of a run.

```yaml
unit: import-cli
entities:
  - name: ClientSettings
    description: The server address and the personal token, kept for the person on their own computer.
    attributes:
      - {name: server, type: address, required: true, constraints: "https address; http allowed only for localhost and 127.0.0.1 (BR1.1)"}
      - {name: token, type: secret text, required: true, constraints: "never printed, logged or put in a report (BR1.2)"}
      - {name: saved_at, type: UTC time, required: true}
    constraints:
      - "stored in the person's own settings folder; readable only by that person (BR1.1)"
      - "MODELHUB_SERVER and MODELHUB_TOKEN override the file for one run (BR1.1)"
  - name: ImportPackage
    description: One model version taken from a bundle, ready to send. Held for one run.
    attributes:
      - {name: model_id, type: text, required: true}
      - {name: commit, type: text, required: true}
      - {name: bundle_name, type: text, required: true}
      - {name: description_text, type: text, required: true, constraints: "the .bundle.json file verbatim"}
      - {name: signature_text, type: text, required: true, constraints: "the .bundle.sig file verbatim"}
      - {name: pieces, type: list of piece, required: true, constraints: "path, index, size and SHA-256 of each"}
      - {name: check_results, type: structured text, required: true, constraints: "what the local verification found (BR1.4)"}
    relationships:
      - {to: ModelReportEntry, cardinality: "1..1", direction: yields}
  - name: Transfer
    description: The live state of sending one package.
    attributes:
      - {name: import_id, type: text, required: false, constraints: "from the service once created"}
      - {name: pieces_total, type: whole number, required: true, min: 1}
      - {name: pieces_sent, type: whole number, required: true, min: 0}
      - {name: bytes_sent, type: whole number, required: true, min: 0}
      - {name: step, type: text, required: true, allowed: [verifying-locally, creating, waiting-for-place, sending, starting, service-working, finished]}
      - {name: attempt, type: whole number, required: true, min: 0, max: 5}
    relationships:
      - {to: ImportPackage, cardinality: "1..1", direction: for}
  - name: ModelReportEntry
    description: One line of the final report.
    attributes:
      - {name: model_id, type: text, required: true}
      - {name: commit, type: text, required: true}
      - {name: result, type: text, required: true, allowed: [imported, skipped, completed, failed]}
      - {name: reason, type: text, required: false, constraints: "required when failed; a fixed explanation for skipped and completed (BR1.9)"}
      - {name: code, type: text, required: false, constraints: "the service's error code, when there is one"}
  - name: RunReport
    description: The whole run's report and exit status.
    attributes:
      - {name: entries, type: list of ModelReportEntry, required: true}
      - {name: imported, type: whole number, required: true, min: 0}
      - {name: skipped, type: whole number, required: true, min: 0}
      - {name: completed, type: whole number, required: true, min: 0}
      - {name: failed, type: whole number, required: true, min: 0}
      - {name: exit_status, type: whole number, required: true, allowed: [0, 1, 2], constraints: "BR1.9"}
```

## Summary

Five entities. `ClientSettings` is the only stored one. `ImportPackage` and `Transfer` exist for one run. `ModelReportEntry` and `RunReport` are what the person reads and what sets the exit status. Importing from an old model-store folder is not built in this version (FDQ5 C), so no entity for it.
