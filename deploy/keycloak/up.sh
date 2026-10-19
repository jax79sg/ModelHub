#!/usr/bin/env bash
# Start the whole stack against a REAL test Keycloak, with the Artifactory stand-in.
# TEST AND DEVELOPMENT ONLY: fixed test secrets, never for a real server.
#   ./up.sh up      write the test secrets and settings, then start everything
#   ./up.sh down    stop and remove everything (and the test data)
# Needs: Docker with Compose, openssl, python3; the images modelhub/{catalog,artifactory-service,
# portal,proxy,smoke}:$RELEASE built (see deploy/README.md and deploy/smoke/run.sh).
# To use the stack from a browser on this computer, map the names to the local machine
# (127.0.0.1 keycloak modelhub.test) in the hosts file; see README.md.
set -euo pipefail
cd "$(dirname "$0")/.."          # deploy/
KC=keycloak
: "${RELEASE:?set RELEASE to the tag the images were built as}"
export MODELHUB_VERSION=$RELEASE SMOKE_VERSION=$RELEASE POSTGRES_IMAGE=${POSTGRES_IMAGE:-postgres:16}
C=(-f compose.yaml -f "$KC/compose.keycloak.yaml" -f "$KC/compose.stack.yaml" --env-file .env)
say() { printf '%s\n' "$*"; }

up() {
  rm -rf secrets
  # the two client secrets come from the realm file, so the stack and Keycloak agree
  portal=$(python3 -c "import json,sys; r=json.load(open('$KC/modelhub-realm.json')); print(next(c['secret'] for c in r['clients'] if c['clientId']=='modelhub'))")
  service=$(python3 -c "import json,sys; r=json.load(open('$KC/modelhub-realm.json')); print(next(c['secret'] for c in r['clients'] if c['clientId']=='modelhub-artifactory-service'))")
  printf '%s\n%s\nartifactory-secret-test-not-for-production\n' "$portal" "$service" | ./ops.sh init-secrets >/dev/null
  openssl req -x509 -newkey rsa:2048 -nodes -days 2 -subj "/CN=modelhub.test" \
    -addext "subjectAltName=DNS:modelhub.test" \
    -keyout secrets/tls_key -out secrets/tls_certificate 2>/dev/null
  chmod 444 secrets/tls_key secrets/tls_certificate
  cat > .env <<ENV
PUBLIC_URL=https://modelhub.test:8443
KEYCLOAK_ISSUER=http://keycloak:8080/realms/modelhub
ARTIFACTORY_URL=http://standins:9100
ARTIFACTORY_REPO=hf-local
MIN_CLIENT_VERSION=0.0.0
ENV
  docker compose "${C[@]}" up -d --wait --wait-timeout 300
  say "Up. Portal: https://modelhub.test:8443  Keycloak: http://keycloak:8080 (test users: see $KC/README.md)"
}

down() {
  docker compose "${C[@]}" down -v --remove-orphans
  rm -rf secrets .env
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  *) say "Usage: ./up.sh up | down  (RELEASE=<tag> must be set)"; exit 2 ;;
esac
