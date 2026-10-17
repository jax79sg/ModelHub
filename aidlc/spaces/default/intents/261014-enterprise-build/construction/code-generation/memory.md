<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
- 2026-10-17T03:03:31Z — Treated the portal as a new package (`server/portal`) reusing the prototype's styles and sanitiser, not as an in-place change to `web/`; the design said "grown from the prototype", and this kept the prototype's 24 tests untouched.

## Deviations
- 2026-10-17T03:03:31Z — The create-time plan decision cannot use a signed file manifest, because the file list is inside the archive and the signed description holds only pieces. Compared the Catalog's recorded files with Artifactory at create when the version is already imported, otherwise decided the plan after unpacking from the bundle's own manifest.
- 2026-10-17T03:03:31Z — The design named a separate migration role but gave it no code; added `MODELHUB_MIGRATION_USER` to the Catalog and import service start-up so the running roles cannot create objects.
- 2026-10-17T03:03:31Z — Plan step 9 (widening PRs per unit) was done as one pass over named gaps plus the requirement-to-test table, not unit by unit.

## Tradeoffs
- 2026-10-17T03:03:31Z — Used Authlib only for the proof key and the sign-in address; its own HTTP client picks `httpx2` when that is installed, which breaks the test transport, so token calls use plain `httpx`.
- 2026-10-17T03:03:31Z — The upgrade-and-return rehearsal retags the same images as the new release instead of building two releases; cheaper and proves the procedure and data survival, but not a schema change.
- 2026-10-17T03:03:31Z — Docker was not run on the developer's machine (it had been unstable); the image build, smoke test and rehearsal were first run in CI and fixed there.

## Open questions
- 2026-10-17T03:03:31Z — Confirm on a real Artifactory: the `jf hf upload` command shape, the repository layout, and that Xet transfers stay off.
- 2026-10-17T03:03:31Z — Keycloak clients and the realm role, the Artifactory repository and service account, the TLS certificate and the pack-signing secrets still have to be provided by their owners.
