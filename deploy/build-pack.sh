#!/usr/bin/env bash
# Build the server pack for one release: the images as archives, the Compose file, the release
# settings, the operator script and guide, a checksum list, and (when a key is given) a signature.
#   RELEASE=1.2.3 OUT=./pack KEY_ID=<signing key id> ./build-pack.sh
# The images must already be built as modelhub/{catalog,artifactory-service,portal,proxy}:$RELEASE.
# The stand-ins and the smoke-test files are never put in a pack.
set -euo pipefail
cd "$(dirname "$0")"
: "${RELEASE:?set RELEASE to the release tag}"
: "${OUT:?set OUT to the folder the pack is made in}"
POSTGRES_BASE=${POSTGRES_BASE:-postgres:16}
APP_IMAGES=(catalog artifactory-service portal proxy)

rm -rf "${OUT}"
mkdir -p "${OUT}/images"

for name in "${APP_IMAGES[@]}"; do
  docker image inspect "modelhub/${name}:${RELEASE}" >/dev/null \
    || { echo "Problem: modelhub/${name}:${RELEASE} is not built" >&2; exit 1; }
  docker save "modelhub/${name}:${RELEASE}" | gzip -n > "${OUT}/images/${name}.tar.gz"
  docker image inspect --format '{{.Id}}' "modelhub/${name}:${RELEASE}" > "${OUT}/images/${name}.id"
done

# The database image: pulled once, its upstream digest recorded, kept under our own tag so the
# server needs no route to the internet.
docker pull "${POSTGRES_BASE}" >/dev/null
digest=$(docker image inspect --format '{{index .RepoDigests 0}}' "${POSTGRES_BASE}")
docker tag "${POSTGRES_BASE}" "modelhub/postgres:${RELEASE}"
docker save "modelhub/postgres:${RELEASE}" | gzip -n > "${OUT}/images/postgres.tar.gz"
printf '%s\n' "${digest}" > "${OUT}/images/postgres.digest"

cat > "${OUT}/release.env" <<ENV
MODELHUB_VERSION=${RELEASE}
POSTGRES_IMAGE=modelhub/postgres:${RELEASE}
ENV

cp compose.yaml env.example ops.sh README.md "${OUT}/"
chmod +x "${OUT}/ops.sh"

if [ -n "${KEY_ID:-}" ]; then
  modelhub pack sign "${OUT}" --key "${KEY_ID}"
else
  echo "Warning: no KEY_ID given; the pack is NOT signed and must not be carried across." >&2
fi
echo "Pack for ${RELEASE} is in ${OUT}"
