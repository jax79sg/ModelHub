# Logical Components: artifactory-service

One container; its logical parts are listed with the failure each one causes.

| Component | Role | Failure domain | Blast radius if it fails |
|-----------|------|----------------|--------------------------|
| Import interface | Routes of contract C1 | artifactory-service container | CLI imports cannot start; browsing continues |
| Import runner | Verifies, uploads and records an import in the background | artifactory-service container | Running imports fail as interrupted and can be rerun |
| Artifactory gateway | The only caller of Artifactory; lists, compares, uploads, deletes | artifactory-service container, Artifactory | Imports and removals; browsing continues |
| Catalog client | Calls the Catalog with the service identity | artifactory-service container, Catalog | Recording and removal marking; imports fail retryably |
| Trusted keys | Holds the key list and checks signatures | artifactory-service schema | New imports refused; browsing continues |
| Retention routines | Setting, due list, decisions, two-step removal | artifactory-service container | Retention screens; nothing is removed |
| Working storage | Pieces and unpacked files | Working volume | Imports refuse with 507; database unaffected |
| Service schema | Jobs, locks, pieces, keys, retention data | PostgreSQL container | The whole service |
