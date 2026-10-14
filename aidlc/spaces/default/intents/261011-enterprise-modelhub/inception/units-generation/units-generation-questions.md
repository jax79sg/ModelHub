# Units Generation Questions

Context: a unit of work is a chunk that goes through the Construction design stages on its own (functional design, quality requirements, quality design and infrastructure design), so **each unit costs four design runs**, each with its own questions and approval. The unit list therefore decides how much design work there is. This stage also fixes what each unit is, how it is deployed, and which unit depends on which; it does not decide the order of work (that is Delivery Planning).

The nine building blocks from Domain Design are: SignIn, PackageSource, ImportClient (the CLI), ImportService, ArtifactoryGateway, Retention, Catalog, Portal and ArtifactoryStandIn. Hosting (FR6) belongs to no single block and needs a unit of its own. The kind of each unit (service, ui, library, packaging) decides which design documents it owes.

## Q1. How should the blocks be grouped into units?

Why we ask: this sets the number of units and so the amount of design work.

- Option A, one unit per deployable part, plus hosting and the stand-in (6 units, 24 design runs):
  1. `catalog` (service): Catalog, its database tables and the data interface.
  2. `artifactory-service` (service): ImportService, ArtifactoryGateway and Retention, the parts that talk to Artifactory.
  3. `portal` (ui): the Portal, grown from the prototype web app.
  4. `import-cli` (service): SignIn, PackageSource and ImportClient, the changes to the existing CLI.
  5. `platform` (packaging): container images, the Compose file, secrets, health checks, logging, the image path through the internal registry, and the upgrade steps (FR6).
  6. `artifactory-stand-in` (service, test only): the ArtifactoryStandIn.
- Option B, the server-side blocks grouped into one unit (5 units, 20 design runs): `server` (Catalog, ImportService, ArtifactoryGateway, Retention) instead of `catalog` and `artifactory-service`; the rest as in A. Fewer runs, but one larger design to hold in mind and less room to build and change the data interface separately.
- Option C, finer (8 units, 32 design runs): A, with Retention as its own `retention` unit and a `common` library unit for sign-in checks, configuration, logging and health helpers. More isolation, noticeably more ceremony.
- Recommendation: A. It matches the containers you chose (intent capture Q9) and keeps each unit a size you can hold in your head.

A. Option A: one unit per deployable part, plus hosting and the stand-in (6 units)
B. Option B: server-side blocks as one unit (5 units)
C. Option C: finer, with Retention and a common library separate (8 units)
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. Where does the code shared by the server-side units live (checking a Keycloak token, loading secrets and configuration, logging, health checks)?

Why we ask: the catalog, the artifactory-service and the portal all need the same security-sensitive helpers. Copying token checking into three places is the kind of duplication that causes security mistakes.

- Option A, a small shared library unit (kind library). Adds one unit (4 more design runs) and every server-side unit depends on it. Pros: token checking is written and tested once. Cons: another unit.
- Option B, each unit keeps its own copy. Pros: no shared unit. Cons: the same sensitive code in three places that can drift apart.
- Option C, it lives inside the `catalog` unit and the others import it from there. Pros: no extra unit. Cons: the portal and the artifactory-service would depend on the data interface just to get helpers.
- Recommendation: A. If you chose Option C at Q1 this is already included.

A. Option A: a shared library unit
B. Option B: each unit keeps its own copy
C. Option C: inside the `catalog` unit
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. Which container runs Retention?

Why we ask: Retention is its own building block (Domain Design decision 3), but a block is not a container. It serves the portal's administrator screens and deletes files through the Artifactory gateway.

- Option A, in the same container as the import service (the `artifactory-service`): everything that touches Artifactory is in one container. Pros: one container holds the Artifactory credentials; one place for the Artifactory gateway at run time. Cons: import and retention restart together.
- Option B, in the portal's container. Pros: one fewer thing between the administrator and Retention. Cons: the portal container would then hold Artifactory deletion rights, which weakens it as the most exposed part.
- Option C, its own container. Pros: fully isolated. Cons: another container to run and secure on one server.
- Recommendation: A.

A. Option A: with the import service in the `artifactory-service` container
B. Option B: inside the portal container
C. Option C: its own container
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. Is the stand-in a unit of its own?

Why we ask: it is never delivered and nothing depends on it, but it needs real work and design (an imitation of the Hugging Face upload and the other Artifactory calls, its list of assumptions, and the checklist for the real system), and the other server-side units are tested against it.

- Option A, its own unit (`artifactory-stand-in`, test only). Pros: its design and approvals are visible; the other units can depend on it for testing. Cons: 4 design runs for something never delivered.
- Option B, part of the `artifactory-service` unit's tests. Pros: no extra unit. Cons: the stand-in's behaviours and assumptions are buried inside another unit's tests and hard to review or reuse.
- Recommendation: A.

A. Option A: its own unit
B. Option B: part of the `artifactory-service` unit's tests
C. Not yet defined
X. Other (please specify)

[Answer]: A
