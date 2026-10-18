# Running the ModelHub server

One Linux server with Docker and the Compose plugin (v2) runs five containers: **proxy** (the only
one reachable from outside, TLS on 443), **portal**, **catalog**, **artifactory-service** and the
**database** (PostgreSQL 16). Sign-in is the organisation's existing Keycloak; the models live in
the existing Artifactory. Nothing here runs the models or serves model files.

Server minimum: 4 cores, 16 GB memory, a 100 GB volume for the database (`catalog-db`) and a
500 GB volume for import working files (`import-work`), plus about 50 GB for the system and images.
The two volumes are separate so a full import disk can never stop the database.

## What you need before the first install

1. From the **Keycloak administrators**: the clients `modelhub` (the portal) and
   `modelhub-artifactory-service` (client credentials), and the realm role `modelhub-admin`.
   The portal's redirect address is `<PUBLIC_URL>/auth/callback`.
2. From the **Artifactory administrators**: a Hugging Face repository (Machine Learning layout) and
   a service account with deploy and delete rights on that repository only. Its token goes in the
   `artifactory_token` secret.
3. The organisation's TLS certificate and key for the host name in `PUBLIC_URL`.
4. The signed **server pack** (images, `compose.yaml`, `release.env`, this guide), carried across
   the air gap with the usual scan.

## First install

```bash
./ops.sh preflight               # checks Docker, .env and 540 GB free (100 GB database + 440 GB import)
cp env.example .env              # then fill it in (PUBLIC_URL, KEYCLOAK_ISSUER, ARTIFACTORY_*)
./ops.sh init-secrets            # random secrets are made; you type the three external ones
cp /path/to/certificate.pem secrets/tls_certificate
cp /path/to/private-key.pem  secrets/tls_key
docker compose --env-file release.env --env-file .env up -d
docker compose ps                # wait until every service is "healthy"
```

Then sign in as an administrator, open **Trusted keys**, add the first signing key (typing back
its fingerprint), make a personal token on the **Tokens** page and run a first
`modelhub import` from an import computer.

The database is prepared by the services themselves at start: a separate migration role
(`modelhub_admin`, used only at start) makes each service's tables and creates the service's own
limited role (`catalog`, `artifactory_service`), which can reach only its own schema.

## Upgrade

1. Verify the new server pack with the trusted key, then load its images.
2. Note what is running: `./ops.sh versions > running-versions.txt`
3. `docker compose stop -t 60`
4. Replace `release.env` with the one from the new pack.
5. `docker compose --env-file release.env --env-file .env up -d` (database steps run at start
   under a lock and keep all data).
6. `docker compose ps` until healthy; sign in and look at the models list.

## Return to the previous release

1. `docker compose stop -t 60`
2. Put the previous `release.env` back (the old images stay on the server).
3. `docker compose --env-file release.env --env-file .env up -d`

A release never removes data in the same version that stopped using it, so a return is safe.

## Secrets

Secrets are files in `secrets/`, mounted at `/run/secrets` in the containers that need them. They
are never in an image, an environment variable or `compose.yaml`. The folder is closed to other
people on the server (mode 700); the files are readable (mode 444) because each container runs as
its own non-root user. Keep `secrets/` out of backups that leave the server.

## What the central monitoring should watch

Any container unhealthy for 5 minutes in business hours; free space under 20% on the database
volume and under 25% on `import-work`; the certificate within 30 days of expiry; memory over 90%
for 10 minutes; proxy 5xx over 5% for 10 minutes. Every container writes JSON lines to standard
output, and each request carries an `X-Request-Id` set by the proxy.

The alerts of the design (ready 503 over 5 minutes, 5xx share over 5% and the list 95th percentile
over 800 ms for 10 minutes, any import failed as `interrupted` or `artifactory_inconsistent`, import
disk under 25% free, Artifactory down over 10 minutes) are listed with the signal each is read from
in `monitoring/alerts.json`; the monitoring team loads them. The share of 5xx lines per service can
be taken from the logs with `python3 monitoring/error_rate.py <log file> --fail-above 0.05`
(`docker compose logs --no-color > logs.txt` makes the file).

`./ops.sh preflight` stops when less than 540 GB are free; on a small test server only, run
`MODELHUB_PREFLIGHT_SMALL=1 ./ops.sh preflight`.

## Not covered here

Backup of the database and working volumes (the data is on named volumes, so a stop-and-copy backup
works today) and restoring the Artifactory repository, which is Artifactory's own matter.
