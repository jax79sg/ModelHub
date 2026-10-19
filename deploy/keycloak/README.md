# A real Keycloak for testing ModelHub

**TEST ONLY. This setup has fixed test secrets and passwords, runs in development mode with no
certificate and no database of its own, and is never for a real server.** It is not part of the
signed server pack. The real server uses the organisation's own Keycloak; the settings below are
what to set up there.

## Start it

Keycloak alone (pinned `quay.io/keycloak/keycloak:26.8.1`, the realm imported at start):

```bash
docker compose -f deploy/keycloak/compose.keycloak.yaml up -d --wait
```

The whole stack beside it, with the Artifactory stand-in standing for Artifactory (the images
must be built first, see `deploy/smoke/run.sh`):

```bash
RELEASE=<tag> deploy/keycloak/up.sh up      # and: ... down
```

The issuer is the container's own name, the same for every part: `http://keycloak:8080/realms/modelhub`.
To use it from a browser on this computer, map the names to the local machine in the hosts file:
`127.0.0.1 keycloak modelhub.test`. Then the portal is at `https://modelhub.test:8443` (its
certificate is made for the test and is not trusted), and Keycloak's own screens at
`http://keycloak:8080` (admin account `admin`, test password in `compose.keycloak.yaml`).

## Test people

| User | Password | Role |
|---|---|---|
| `ada` | `ada-password-test-not-for-production` | none (an ordinary person) |
| `root` | `root-password-test-not-for-production` | `modelhub-admin` |

## What to set up in the organisation's Keycloak

The same as `modelhub-realm.json`, with real secrets:

- **Realm** `modelhub`; the stack's `KEYCLOAK_ISSUER` is its address, for example
  `https://keycloak.example.org/realms/modelhub`.
- **Realm role** `modelhub-admin`, given to the people who may use the administrator screens.
- **Client `modelhub`** (the portal): confidential; authorisation code flow only, with a proof
  key (PKCE, method `S256`); scope `openid`; valid redirect addresses
  `http://localhost:8000/auth/callback` and `https://modelhub.test:8443/auth/callback` (use the
  portal's real address, `<PUBLIC_URL>/auth/callback`); an **audience mapper** adding the
  audience `modelhub` to the access token. Its secret goes in the portal's
  `keycloak_client_secret` file.
- **Client `modelhub-artifactory-service`** (the import service): confidential; client credentials
  only (service account, no browser flow); the same audience mapper. Its secret goes in the
  import service's `service_client_secret` file.
- **Token claims the code checks:** `iss` (the issuer above), `aud` containing `modelhub`, `sub`,
  `preferred_username`, `realm_access` with the roles (`modelhub-admin` for administrators), and
  for the import service's token `azp` equal to `modelhub-artifactory-service`.

## What the tests do

`server/e2e/tests/test_real_keycloak.py` starts this Keycloak, signs in to the portal in Chrome as
`ada` and as `root`, makes a personal token, and shows the import service's client-credentials
token accepted by the Catalog. CI runs it. It skips where Docker or Chrome is missing.
