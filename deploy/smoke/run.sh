#!/usr/bin/env bash
# Whole-stack smoke test and upgrade-and-return rehearsal, for CI (and any Docker host).
# Needs the images built as modelhub/{catalog,artifactory-service,portal,proxy,smoke}:$FROM.
#   FROM=<release tag>  TO=<another tag>  ./run.sh
set -euo pipefail
cd "$(dirname "$0")/.."          # deploy/
: "${FROM:?set FROM to the release tag the images were built as}"
: "${TO:=${FROM}-next}"
POSTGRES_IMAGE=${POSTGRES_IMAGE:-postgres:16}
export SMOKE_VERSION=$FROM   # the outside systems are not upgraded with the product
PRODUCT=(proxy portal artifactory-service catalog database)

C=(-f compose.yaml -f smoke/compose.smoke.yaml --env-file .env)
cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    echo "== the smoke test failed; the last log lines of each container follow"
    MODELHUB_VERSION=${CURRENT:-$FROM} POSTGRES_IMAGE=$POSTGRES_IMAGE \
      docker compose "${C[@]}" logs --tail 60 --no-color || true
  fi
  MODELHUB_VERSION=${CURRENT:-$FROM} POSTGRES_IMAGE=$POSTGRES_IMAGE \
    docker compose "${C[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf secrets .env
}
trap cleanup EXIT
cp smoke/env.smoke .env
rm -rf secrets
printf 'portal-secret\nservice-secret\nartifactory-secret-%s\n' "$RANDOM$RANDOM" | ./ops.sh init-secrets >/dev/null
openssl req -x509 -newkey rsa:2048 -nodes -days 2 -subj "/CN=modelhub.test" \
  -addext "subjectAltName=DNS:modelhub.test" \
  -keyout secrets/tls_key -out secrets/tls_certificate 2>/dev/null
chmod 444 secrets/tls_key secrets/tls_certificate

step() { printf '\n== %s\n' "$*"; }
up() {   # up <tag>
  CURRENT=$1
  MODELHUB_VERSION=$1 POSTGRES_IMAGE=$POSTGRES_IMAGE docker compose "${C[@]}" up -d --wait --wait-timeout 300
}
drive() { # drive <tag> <mode>
  MODELHUB_VERSION=$1 POSTGRES_IMAGE=$POSTGRES_IMAGE docker compose "${C[@]}" --profile driver run --rm driver python /smoke/driver.py "$2"
}
stop() {   # stop the product, as an operator does; the stand-ins for outside systems stay up
  MODELHUB_VERSION=$1 POSTGRES_IMAGE=$POSTGRES_IMAGE docker compose "${C[@]}" stop -t 60 "${PRODUCT[@]}"
}

step "release $FROM: start, first import"
up "$FROM"
drive "$FROM" import

step "upgrade to $TO (the data must survive)"
stop "$FROM"
for name in catalog artifactory-service portal proxy; do docker tag "modelhub/$name:$FROM" "modelhub/$name:$TO"; done
up "$TO"
drive "$TO" check

step "return to $FROM (the data must still be there)"
stop "$TO"
up "$FROM"
drive "$FROM" check

step "no route out: a product container cannot reach the internet"
inside() { # inside <service> <command...>: run a command in a running product container
  MODELHUB_VERSION=$FROM POSTGRES_IMAGE=$POSTGRES_IMAGE docker compose "${C[@]}" exec -T "$@"
}
for name in catalog portal artifactory-service; do
  # the control: the container is running and reaches the database inside the network ...
  inside "$name" python -c "import socket; socket.create_connection(('database', 5432), 3).close()" \
    || { echo "Problem: $name cannot reach the database, so the check below would prove nothing"; exit 1; }
  # ... and the test: it cannot reach an address on the internet
  if inside "$name" python -c "import socket; socket.create_connection(('1.1.1.1', 443), 3).close()" >/dev/null 2>&1; then
    echo "Problem: $name can reach the internet"; exit 1
  fi
  echo "$name reaches the database and cannot reach the internet"
done
inside proxy curl --fail --silent --insecure https://127.0.0.1:8443/healthz >/dev/null \
  || { echo "Problem: the proxy does not answer, so the check below would prove nothing"; exit 1; }
if inside proxy curl --silent --max-time 3 https://1.1.1.1 >/dev/null 2>&1; then
  echo "Problem: proxy can reach the internet"; exit 1
fi
echo "proxy answers and cannot reach the internet"

step "no secret may be in the logs of any container"
LOGS=$(mktemp)
MODELHUB_VERSION=$FROM POSTGRES_IMAGE=$POSTGRES_IMAGE docker compose "${C[@]}" logs --no-color >"$LOGS" 2>&1
python3 smoke/check_logs.py secrets "$LOGS" || { rm -f "$LOGS"; exit 1; }
rm -f "$LOGS"

step "smoke test and rehearsal passed"
