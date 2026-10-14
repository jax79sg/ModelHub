# Logical Components: catalog

The Catalog is one service with one database. Its logical parts are listed with failure domains.

| Component | Role | Failure domain | Blast radius if it fails |
|-----------|------|----------------|--------------------------|
| HTTP interface | Routes of contracts C2 and C3 | Catalog container | Everything in the system that reads model information |
| Store routine | Writes a version with its files, documents, trail row and summary in one transaction | Catalog container and its database | Imports cannot be recorded; reads continue |
| List and search routines | Read the summary table and search indexes | Catalog container and its database | The portal's lists |
| Document reader | Serves stored documents as data | Catalog container and its database | README and pictures; lists continue |
| Token service | Makes, lists, revokes and checks personal tokens | Catalog container and its database | CLI sign-in (imports cannot start); browsing continues |
| Migration runner | Applies database steps at start-up | Start-up of the Catalog | The Catalog does not start; data untouched |
| PostgreSQL (Catalog schema) | Holds all Catalog data | Database container and its volume | The whole Catalog |
