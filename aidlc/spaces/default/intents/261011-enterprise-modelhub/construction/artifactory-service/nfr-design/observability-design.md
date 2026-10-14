# Observability Design: artifactory-service

What operators can see of imports and retention.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR6.1 | Request and import-event lines | Access line per request plus a line per import state change (import id, model, step, bytes); the Artifactory tool's raw output is logged only after redaction and never returned to callers. |
| NFR6.2 | Ready check with a critical database | Database critical; Artifactory and Catalog checks non-critical; working-volume free space reported. |
| NFR6.3 | Progress readable by the CLI and operators | Step, bytes done and total, update time and error code are in the job row and the import call. |
| NFR6.4 | Alert thresholds | Ready 503 over 5 minutes; any import failed as interrupted or artifactory_inconsistent; working disk under 25% free; Artifactory down over 10 minutes. |
| NFR6.5 | Fixed event codes | import_created, import_skipped, import_done, import_failed, key_added, key_revoked, retention_decided, version_removed. |
