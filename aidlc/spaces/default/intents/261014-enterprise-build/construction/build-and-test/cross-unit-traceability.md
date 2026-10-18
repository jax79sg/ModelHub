# Cross-Unit Traceability

## Verdict

PASS: 63 of 63 requirement IDs (every `FR` and `NFR` named in `requirements.md`) are covered with status OK by a unit `traceability.json`, and every target file exists. The user-stories stage was skipped, so there are no `AC` IDs to enumerate. Uncovered: none. (An earlier version of this file said "0 of 0"; it enumerated nothing and was redone on 2026-10-18 during CI Pipeline; FR2.7 was missing from the catalog's file and was added.)

## Per-ID coverage

| ID | Owning unit | Target file | Verdict |
|---|---|---|---|
| FR1 | artifactory-service, import-cli | server/artifactory_service/src/modelhub_artifactory_service/importer.py | OK |
| FR1.1 | artifactory-service, import-cli | server/artifactory_service/src/modelhub_artifactory_service/importer.py | OK |
| FR1.2 | artifactory-service, import-cli | server/artifactory_service/src/modelhub_artifactory_service/app.py | OK |
| FR1.3 | artifactory-service | server/artifactory_service/src/modelhub_artifactory_service/record_builder.py | OK |
| FR1.4 | artifactory-service, import-cli | server/artifactory_service/src/modelhub_artifactory_service/importer.py | OK |
| FR1.5 | artifactory-service | server/artifactory_service/src/modelhub_artifactory_service/importer.py | OK |
| FR1.6 | artifactory-service | server/artifactory_service/src/modelhub_artifactory_service/importer.py | OK |
| FR1.7 | artifactory-service | server/artifactory_service/src/modelhub_artifactory_service/names.py | OK |
| FR1.8 | artifactory-service | server/artifactory_service/src/modelhub_artifactory_service/gateway.py | OK |
| FR1.9 | artifactory-service, import-cli | server/artifactory_service/src/modelhub_artifactory_service/retry.py | OK |
| FR1.10 | import-cli | src/modelhub/cli.py | OK |
| FR1.11 | import-cli | src/modelhub/importer.py | OK |
| FR1.12 | artifactory-service | server/artifactory_service/src/modelhub_artifactory_service/importer.py | OK |
| FR1.13 | import-cli | src/modelhub/progress.py | OK |
| FR1.14 | artifactory-service | server/artifactory_service/src/modelhub_artifactory_service/importer.py | OK |
| FR2 | artifactory-service, catalog | server/catalog/src/modelhub_catalog/records.py | OK |
| FR2.1 | catalog | server/catalog/src/modelhub_catalog/records.py | OK |
| FR2.2 | catalog | server/catalog/src/modelhub_catalog/store.py | OK |
| FR2.3 | catalog | server/catalog/src/modelhub_catalog/store.py | OK |
| FR2.4 | catalog | server/catalog/src/modelhub_catalog/records.py | OK |
| FR2.5 | catalog | server/catalog/src/modelhub_catalog/store.py | OK |
| FR2.6 | catalog | server/catalog/src/modelhub_catalog/records.py | OK |
| FR2.7 | catalog | server/catalog/tests/test_store_put.py | OK |
| FR2.8 | artifactory-service | server/artifactory_service/src/modelhub_artifactory_service/record_builder.py | OK |
| FR3 | catalog, common, portal | server/portal/src/modelhub_portal/app.py | OK |
| FR3.1 | common, portal | server/portal/src/modelhub_portal/app.py | OK |
| FR3.2 | portal | server/portal/src/modelhub_portal/catalog_client.py | OK |
| FR3.3 | portal | server/portal/src/modelhub_portal/app.py | OK |
| FR3.4 | catalog | server/catalog/src/modelhub_catalog/store.py | OK |
| FR3.5 | catalog | server/catalog/src/modelhub_catalog/store.py | OK |
| FR3.6 | portal | server/portal/src/modelhub_portal/app.py | OK |
| FR3.7 | portal | server/portal/src/modelhub_portal/app.py | OK |
| FR3.8 | portal | server/portal/src/modelhub_portal/app.py | OK |
| FR4 | artifactory-service, catalog, common, portal | server/portal/src/modelhub_portal/app.py | OK |
| FR4.1 | common, portal | server/portal/src/modelhub_portal/app.py | OK |
| FR4.2 | artifactory-service, common | server/common/src/modelhub_common/tokens.py | OK |
| FR4.3 | common, portal | server/portal/src/modelhub_portal/app.py | OK |
| FR4.4 | catalog, portal | server/portal/src/modelhub_portal/app.py | OK |
| FR4.5 | artifactory-service, catalog | server/catalog/src/modelhub_catalog/store.py | OK |
| FR4.6 | catalog, portal | server/portal/src/modelhub_portal/app.py | OK |
| FR5 | artifactory-service, catalog, portal | server/portal/src/modelhub_portal/app.py | OK |
| FR5.1 | artifactory-service | server/artifactory_service/src/modelhub_artifactory_service/retention.py | OK |
| FR5.2 | artifactory-service | server/artifactory_service/src/modelhub_artifactory_service/retention.py | OK |
| FR5.3 | artifactory-service | server/artifactory_service/src/modelhub_artifactory_service/retention.py | OK |
| FR5.4 | artifactory-service | server/artifactory_service/src/modelhub_artifactory_service/retention.py | OK |
| FR5.5 | artifactory-service, catalog | server/catalog/src/modelhub_catalog/store.py | OK |
| FR5.6 | artifactory-service | server/artifactory_service/src/modelhub_artifactory_service/retention.py | OK |
| FR5.7 | artifactory-service, portal | server/portal/src/modelhub_portal/app.py | OK |
| FR6 | artifactory-service, common, platform, portal | server/portal/src/modelhub_portal/main.py | OK |
| FR6.1 | platform | deploy/compose.yaml | OK |
| FR6.2 | platform | deploy/build-pack.sh | OK |
| FR6.3 | platform | deploy/compose.yaml | OK |
| FR6.4 | artifactory-service, common, platform, portal | server/portal/src/modelhub_portal/main.py | OK |
| FR6.5 | common, platform | deploy/proxy/nginx.conf | OK |
| FR6.6 | platform | deploy/smoke/run.sh | OK |
| FR7 | artifactory-stand-in | server/stand_in/src/modelhub_stand_in/app.py | OK |
| FR7.1 | artifactory-stand-in | server/stand_in/src/modelhub_stand_in/app.py | OK |
| FR7.2 | artifactory-stand-in | server/stand_in/src/modelhub_stand_in/assumptions.json | OK |
| FR7.3 | artifactory-stand-in | server/stand_in/src/modelhub_stand_in/register.py | OK |
| FR8 | import-cli | src/modelhub/cli.py | OK |
| FR8.1 | import-cli | src/modelhub/cli.py | OK |
| NFR1 | platform | server/e2e/tests/test_whole_stack.py | OK |
| NFR10 | artifactory-stand-in, import-cli | tests/test_import_cli.py | OK |
