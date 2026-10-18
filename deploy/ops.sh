#!/usr/bin/env bash
# Operator helper for the server stack. Run it from this folder (next to compose.yaml).
#   ./ops.sh preflight        check the server is ready for a first install
#   ./ops.sh init-secrets     make the secret files (random ones generated, others asked for)
#   ./ops.sh load-images <pack>  load a verified server pack's images into Docker
#   ./ops.sh versions         note the release tags now running (keep this for a return)
set -euo pipefail
cd "$(dirname "$0")"

SECRETS_DIR="secrets"
GENERATED=(database_migration_password catalog_db_password service_db_password token_hash_pepper)
ASKED=(keycloak_client_secret_portal keycloak_client_secret_service artifactory_token)
PLACED=(tls_certificate tls_key)

say() { printf '%s\n' "$*"; }
fail() { printf 'Problem: %s\n' "$*" >&2; exit 1; }

preflight() {
  command -v docker >/dev/null || fail "docker is not installed"
  docker compose version >/dev/null 2>&1 || fail "the Docker Compose plugin (v2) is not installed"
  [ -f compose.yaml ] || fail "compose.yaml is not in this folder"
  [ -f .env ] || fail ".env is missing; copy env.example to .env and fill it in"
  grep -Eq '^PUBLIC_URL=https://' .env || fail "PUBLIC_URL in .env must start with https://"
  for name in KEYCLOAK_ISSUER ARTIFACTORY_URL ARTIFACTORY_REPO; do
    grep -Eq "^${name}=.+" .env || fail "${name} is empty in .env"
  done
  for name in "${PLACED[@]}"; do
    [ -s "${SECRETS_DIR}/${name}" ] || say "Still to do: put the organisation's ${name} file at ${SECRETS_DIR}/${name}"
  done
  docker compose --env-file .env config --quiet 2>/dev/null \
    || say "Note: compose.yaml needs release.env (from the server pack) as well as .env"
  root=$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || echo /)
  say "Free space on the Docker data folder:"
  df -h "${root}" | tail -1
  say "Minimums: 100 GB for the database volume, 440 GB for the import working volume (planned at 500 GB), 16 GB memory."
  free_gb=$(( $(df -Pk "${root}" | awk 'NR==2 {print $4}') / 1024 / 1024 ))
  if [ "${free_gb}" -lt 540 ]; then
    if [ "${MODELHUB_PREFLIGHT_SMALL:-}" = "1" ]; then
      say "Note: only ${free_gb} GB are free (540 GB are needed); continuing because MODELHUB_PREFLIGHT_SMALL=1 says this is a small test server."
    else
      fail "only ${free_gb} GB are free on the Docker data folder; 540 GB are needed (100 GB database + 440 GB import area). For a small test server only, run: MODELHUB_PREFLIGHT_SMALL=1 ./ops.sh preflight"
    fi
  fi
  say "Preflight finished."
}

init_secrets() {
  force=${1:-}
  umask 077
  mkdir -p "${SECRETS_DIR}"
  chmod 700 "${SECRETS_DIR}"
  for name in "${GENERATED[@]}"; do
    file="${SECRETS_DIR}/${name}"
    if [ -e "${file}" ] && [ "${force}" != "--force" ]; then say "Kept ${name} (already there)"; continue; fi
    openssl rand -base64 33 | tr -d '\n=+/' > "${file}"
    say "Made ${name}"
  done
  for name in "${ASKED[@]}"; do
    file="${SECRETS_DIR}/${name}"
    if [ -e "${file}" ] && [ "${force}" != "--force" ]; then say "Kept ${name} (already there)"; continue; fi
    printf 'Value for %s (typed with no echo): ' "${name}"
    read -rs value; printf '\n'
    [ -n "${value}" ] || fail "${name} was empty"
    printf '%s' "${value}" > "${file}"
  done
  # The containers run as their own non-root users, so they must be able to read the files.
  # The folder stays closed to other people on this server (mode 700); the files are mode 444.
  chmod 444 "${SECRETS_DIR}"/* 2>/dev/null || true
  say "Secrets are in ${SECRETS_DIR}/. Place tls_certificate and tls_key there too."
}

load_images() {
  pack=${1:?usage: ./ops.sh load-images <pack folder>}
  command -v modelhub >/dev/null \
    || fail "the modelhub program is needed to verify the pack: run 'modelhub pack verify ${pack}' on a computer that has it, then try again"
  modelhub pack verify "${pack}" || fail "the pack did not verify; nothing was loaded"
  for archive in "${pack}"/images/*.tar.gz; do
    say "Loading ${archive##*/}"
    gunzip -c "${archive}" | docker load
  done
  say "Images loaded. Now: docker compose --env-file ${pack}/release.env --env-file .env up -d"
}

versions() {
  docker compose ps --format '{{.Service}} {{.Image}}'
}

case "${1:-}" in
  preflight) preflight ;;
  init-secrets) init_secrets "${2:-}" ;;
  load-images) load_images "${2:-}" ;;
  versions) versions ;;
  *) say "Usage: ./ops.sh preflight | init-secrets [--force] | load-images <pack> | versions"; exit 2 ;;
esac
