# Entities: artifactory-stand-in

Inputs: `unit-of-work.md` (U3), `requirements.md` (FR7, NFR9), `contract-summary.md` (C5), and the answers in `functional-design-questions.md` (written FDQ). The stand-in keeps everything in memory and in a temporary folder for the length of a test; nothing is stored between runs. These are its logical entities, not database tables.

```yaml
unit: artifactory-stand-in
entities:
  - name: StandInServer
    description: One running copy of the stand-in, owned by one test run. Holds the settings and all the state below.
    attributes:
      - {name: token, type: secret text, required: true, constraints: "the one bearer token accepted (BR1.1)"}
      - {name: write_allowed, type: boolean, required: true, default: true, constraints: "when false, mutating calls answer 403 (BR1.1)"}
      - {name: layout, type: text, required: true, allowed: [flat, nested], default: flat, constraints: "chosen at start; never changes while running (BR1.12)"}
      - {name: keep_limit_bytes, type: whole number, required: true, default: 1048576, min: 0, constraints: "files up to this size are kept; larger ones are virtual (BR1.9)"}
      - {name: overwrite_allowed, type: boolean, required: true, default: false, constraints: "when false, a repeat of a complete version answers 409 (BR1.3)"}
      - {name: port, type: whole number, required: true, constraints: "free local port picked at start; bound to 127.0.0.1 only (BR1.14)"}
    relationships:
      - {to: Repository, cardinality: "1..*", direction: owns}
      - {to: RecordedCall, cardinality: "0..*", direction: owns}
      - {to: FailureSwitch, cardinality: "0..*", direction: owns}
  - name: Repository
    description: A local Hugging Face repository (Machine Learning layout) identified by its key.
    attributes:
      - {name: key, type: text, required: true, unique: true, constraints: "letters, numbers, hyphen, underscore"}
      - {name: type, type: text, required: true, allowed: [huggingfaceml], default: huggingfaceml}
    relationships:
      - {to: StoredVersion, cardinality: "0..*", direction: owns}
  - name: StoredVersion
    description: One model revision in a repository, with the files uploaded for it.
    attributes:
      - {name: organisation, type: text, required: true, constraints: "naming rule BR1.2"}
      - {name: model, type: text, required: true, constraints: "naming rule BR1.2"}
      - {name: revision, type: text, required: true, constraints: "40 hexadecimal characters once committed (BR1.4); naming rule BR1.2 before"}
      - {name: state, type: text, required: true, allowed: [partial, complete], constraints: "absent versions do not exist as rows (BR1.5)"}
      - {name: committed_at, type: UTC time, required: false, constraints: "set when state becomes complete"}
    constraints:
      - "unique on (repository, organisation, model, revision)"
    relationships:
      - {to: StoredFile, cardinality: "0..*", direction: owns}
  - name: StoredFile
    description: One file of a version. Either kept (content held) or virtual (only name, size and checksum held).
    attributes:
      - {name: path, type: text, required: true, constraints: "relative; no '..', no leading slash, no backslash (BR1.15)"}
      - {name: size_bytes, type: whole number, required: true, min: 0}
      - {name: sha256, type: text, required: true, constraints: "64 hexadecimal characters; for kept files computed from the content, for virtual files taken from the declaration (BR1.6)"}
      - {name: content_mode, type: text, required: true, allowed: [kept, virtual], constraints: "kept when size is at most keep_limit_bytes or the test marks it keep (BR1.9)"}
      - {name: transfer, type: text, required: true, allowed: [regular, large-file], constraints: "large-file means it came through the large-file batch call"}
    relationships:
      - {to: StoredVersion, cardinality: "*..1", direction: belongs-to}
  - name: RecordedCall
    description: One call received, kept for the test to read afterwards.
    attributes:
      - {name: sequence, type: whole number, required: true, unique: true}
      - {name: method, type: text, required: true}
      - {name: path, type: text, required: true}
      - {name: status, type: whole number, required: true}
      - {name: received_at, type: UTC time, required: true}
      - {name: switch_fired, type: text, required: false, constraints: "name of the failure switch that decided the answer, when one did"}
    constraints:
      - "never holds the token or request bodies of kept files (BR1.11)"
  - name: FailureSwitch
    description: A test's instruction to misbehave on purpose.
    attributes:
      - {name: kind, type: text, required: true, allowed: [unauthorised, forbidden, conflict, name-refused, server-error, slow, cut-transfer, half-version]}
      - {name: scope, type: text, required: true, allowed: [any-call, upload-calls, large-file-batch, commit, listing, fetch, delete], default: any-call}
      - {name: after_calls, type: whole number, required: true, default: 0, min: 0, constraints: "fires on the call after this many matching calls"}
      - {name: times, type: whole number, required: true, default: 1, min: 1, constraints: "how many calls it affects; 'until cleared' is a separate flag"}
      - {name: sticky, type: boolean, required: true, default: false}
    relationships:
      - {to: StandInServer, cardinality: "*..1", direction: belongs-to}
  - name: Assumption
    description: One behaviour the stand-in has that JFrog's documentation does not state in so many words.
    attributes:
      - {name: id, type: text, required: true, unique: true, constraints: "A1, A2, ..."}
      - {name: behaviour, type: text, required: true}
      - {name: basis, type: text, required: true, allowed: [documented, inferred, invented]}
      - {name: source, type: text, required: false, constraints: "the JFrog page when basis is documented or inferred"}
      - {name: confirm_on_real, type: boolean, required: true, constraints: "true puts it on the checklist (BR1.13)"}
    relationships:
      - {to: ChecklistItem, cardinality: "0..1", direction: produces}
  - name: ChecklistItem
    description: One line of the list to check on a real Artifactory.
    attributes:
      - {name: assumption_id, type: text, required: true, unique: true}
      - {name: what_to_check, type: text, required: true}
      - {name: expected, type: text, required: true}
      - {name: confirmed, type: text, required: true, allowed: [open, confirmed, differs], default: open}
```

## Summary

Eight entities. `StandInServer` owns the settings, the repositories, the recorded calls and the failure switches. A `Repository` holds `StoredVersion`s and a version holds `StoredFile`s; a version is `partial` until the commit call and `complete` after. `Assumption` and `ChecklistItem` are the documentation the stand-in must ship (FR7.2, FR7.3): they are data files read by tests, not state kept while running.
