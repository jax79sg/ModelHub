# Unit Dependencies

## Dependency graph

There is one unit, so there are no edges: U1 depends on no other unit. It builds on the existing stack (Catalog, import service, portal) only through configuration values, which is not a unit dependency.

## Integration points

- The realm file's issuer, client ids and secrets feed the stack's `KEYCLOAK_ISSUER`, `MODELHUB_KEYCLOAK_CLIENT_ID`, `MODELHUB_SERVICE_CLIENT_ID` and the two client-secret files.
- The real sign-in tests use the existing whole-stack harness in `server/e2e/` and the portal Chrome test.

## Parallel development opportunities

None: a single unit.

## Skeleton

U1 is the first and only unit, so it is also the integrated slice: it runs end to end (real Keycloak, the stack, the sign-in) as soon as its own parts exist.

```yaml
units:
  - name: keycloak
    kind: packaging
    depends_on: []
```
