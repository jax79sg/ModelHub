<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->


- 2026-10-12T13:00:00Z — read FDQ2 C (keep small, virtual large) as: a fetch of a virtual file answers 501 rather than invented bytes, so no test silently passes on fake content.
<!-- aidlc-wave-memory:artifactory-stand-in:015eeeb623789f4190d396473a229b65dc15ffaa5c36e856ece2cae063ac81fc -->

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->


- 2026-10-12T13:00:00Z — the engine started with artifactory-stand-in, not common as bolt-plan.md lists; both have no dependencies and the engine walks the dependency graph, not the Bolt plan.
<!-- aidlc-wave-memory:artifactory-stand-in:3889aefaf55893f808678b306ef50b9dbac664368f14dcf1c0a12d0b333d7cd5 -->


- 2026-10-12T13:00:00Z — the traceability sensor needs every FR in upstream_ids (no stories exist), so the 57 FRs owned by other units are listed N/A; only FR7 to FR7.3 map to rules.
<!-- aidlc-wave-memory:artifactory-stand-in:f4715b47b01963458d75d2e24a7b7df3816cb5b44e0c8bb2fd7fe76c1477e91c -->


- 2026-10-12T15:10:00Z — FDQ3 B changed an approved Catalog rule (BR1.2/BR1.12 and its state table); edited in place and noted in the Catalog diary.
<!-- aidlc-wave-memory:artifactory-service:01fbc803020ec3d2b97fcb18894f758a10fc64a1f6abc4678bf277d7e09332be -->


- 2026-10-12T15:10:00Z — decided that the plan 'finish' still needs every piece sent (the documents for the Catalog are inside the bundle); the CLI design must respect this.
<!-- aidlc-wave-memory:artifactory-service:95d04a20dcee9555cc76e411a183fe62a317db8d1b1405eb2a36df4f2d99cf2b -->


- 2026-10-12T15:40:00Z — FR8 (old folder) is designed as Deferred, not built (FDQ5 C); the requirement says 'designed now, built after the first version', so the design is a reserved option only. The earlier scope said the same. Human may reverse at the gate.
<!-- aidlc-wave-memory:import-cli:c2d6554c0882d453fe393d5152cefaab952e55a8befaa6c54fee5c29482b4f38 -->


- 2026-10-12T16:20:00Z — a UI unit owes no rules or entities file; I wrote rules.md because the portal has real access and failure rules and the sensor ties requirements to rule IDs.
<!-- aidlc-wave-memory:portal:ebcceb1e3e141273fd5fd199e2788672babf2070b311cf35e1c9041ef20c780e -->


- 2026-10-12T16:20:00Z — the prototype's download, raw and JSON routes are removed (the portal serves no model file; other programs use the Catalog).
<!-- aidlc-wave-memory:portal:4d7da2194bd1a7d382a60b80635e71934a57066bfef7572aba02d933866d732b -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->


- 2026-10-12T14:10:00Z — FDQ6 B (delete documents on removal) was the human's choice against the recommendation: space is freed but a removed version's card can no longer be shown, and the README text is cleared from search.
<!-- aidlc-wave-memory:catalog:3f627d3d10fddc57e5f0260b3653562fa344a627a1163ad02f4b40de2d445f3b -->

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->

- 2026-10-12T13:00:00Z — answers for the 409 body, the 400 name-refusal body, 404 on delete of an absent version and the two layouts are invented and on the checklist for a real Artifactory (X1).
<!-- aidlc-wave-memory:artifactory-stand-in:fc0b0e8655fbd1a67ef99fe917232fc47ed35337fb4933ea521141a264246f03 -->

- 2026-10-12T13:30:00Z — getting a service token with client credentials (C6) is used only by artifactory-service, so it is left to that unit rather than added to common.
<!-- aidlc-wave-memory:common:e858ff6410fab82eb8b1855c11f708faa2f95919bd554573326d04632754b822 -->

- 2026-10-12T14:10:00Z — decided that a skipped or repaired import still adds one trail row (BR1.13); an earlier open question, now an assumption the human can reverse at the gate.
<!-- aidlc-wave-memory:catalog:56eb5d205e33c1fb66799892084dd4139c07fd0cf816d5db64728791f6b77eba -->

- 2026-10-12T14:10:00Z — re-importing a removed version is refused by the Catalog (409); artifactory-service must decide what the CLI is told.
<!-- aidlc-wave-memory:catalog:b885c535de9ebb97637e774c5f12ea4e5773e47d4b0b86230270744a31c53954 -->

- 2026-10-12T14:10:00Z — 16 MiB per document and 20 active tokens per person are my defaults, not answers.
<!-- aidlc-wave-memory:catalog:d9537a3e478d9e03fc302890eea04c369365d8d4e96aad6b59cacc2bbfae1dfe -->

- 2026-10-12T15:10:00Z — getting the service token for Catalog calls (client credentials) is this unit's job, as common leaves it out; shape it in NFR/infrastructure design.
<!-- aidlc-wave-memory:artifactory-service:dcd2370790ef469c1ab44ccf55ff729971d094698589dfb26e29ee66f945dc48 -->

- 2026-10-12T15:10:00Z — retention default is 365 days (FR5.1); maximum 3650 and max_running_imports 2 are my defaults.
<!-- aidlc-wave-memory:artifactory-service:3f00f4267caec45b746ce63e897bfb778cf6bc25eee91835e826b9cac761c8df -->

- 2026-10-12T15:40:00Z — BR1.14 relies on the service answering 426 for a too-old program (contract C1 versioning); artifactory-service has no rule for it yet, so it must be added at its NFR/infrastructure design or here as a knock-on.
<!-- aidlc-wave-memory:import-cli:985ee87790c345c3df71ede0e81723a37a46a279e5daba4c59acbbd846f8e104 -->

- 2026-10-12T15:40:00Z — whether the server's address uses a certificate the import computers trust is not known; tied to the organisation's setup.
<!-- aidlc-wave-memory:import-cli:da23341f1981d033e8a4669ca7cd793ff6b4242240627c3d171aa07d7cc5a9b0 -->

- 2026-10-12T16:20:00Z — FR3.8 ('signed-in people keep working until their session ends') holds only while the Keycloak access token is valid; ask the Keycloak administrators about a longer access-token lifetime.
<!-- aidlc-wave-memory:portal:174ea943eb9af89a04674630e324924451544ce33bad531d7acb55a80af70979 -->

- 2026-10-12T16:20:00Z — the fetch snippets follow JFrog's documentation and are on the checklist for a real Artifactory.
<!-- aidlc-wave-memory:portal:1097b49ea49a9444dac3abbd00430ba7a4cb476f6b0d07436bc41216ce88a8b3 -->
