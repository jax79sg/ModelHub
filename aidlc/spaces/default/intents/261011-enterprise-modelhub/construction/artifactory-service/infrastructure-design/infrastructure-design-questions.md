# Infrastructure Design Questions: artifactory-service

No open questions. The two choices that apply to every server unit were answered at the Catalog (one production stack only; alerts routed by the existing central monitoring). The rest follows from the approved targets (bundles up to 200 GB, two imports at once, a 500 GB working volume, its own schema in the same PostgreSQL). The way people and the CLI reach this service is decided in the `platform` unit.
