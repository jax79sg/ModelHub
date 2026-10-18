# One image recipe for the three Python services (portal, catalog, artifactory-service).
# Build with: docker build -f deploy/Dockerfile --build-arg UNIT=catalog -t modelhub/catalog:<release> .
# The Artifactory stand-in and the test helpers are never installed here (checked in CI).
ARG PYTHON_IMAGE=python:3.12-slim

FROM ${PYTHON_IMAGE} AS build
ARG UNIT
WORKDIR /src
COPY pyproject.toml README.md ./
COPY deploy/constraints.txt /constraints.txt
COPY src ./src
COPY web ./web
COPY server/common ./server/common
COPY server/catalog ./server/catalog
COPY server/artifactory_service ./server/artifactory_service
COPY server/portal ./server/portal
RUN python -m venv /opt/venv \
 && case "${UNIT}" in \
      catalog)             PKGS="./server/common ./server/catalog" ;; \
      artifactory_service) PKGS=". ./server/common ./server/artifactory_service" ;; \
      portal)              PKGS="./web ./server/common ./server/portal" ;; \
      *) echo "UNIT must be catalog, artifactory_service or portal" >&2; exit 1 ;; \
    esac \
 && /opt/venv/bin/pip install --no-cache-dir -c /constraints.txt ${PKGS}

FROM ${PYTHON_IMAGE}
ARG UNIT
ARG RELEASE=dev
# The JFrog CLI, in the import service image only: downloaded here, on the internet side, for the
# image's CPU type and checked against the pinned checksum; the running container never downloads.
# The default upload path is still huggingface_hub; `jf hf upload` is the documented alternative.
ARG JF_VERSION=2.122.0
ARG JF_SHA256_AMD64=2563d19de8a42ac97c80fe9cac6928364c4a5441074bd09bb38b3891532d5738
ARG JF_SHA256_ARM64=e394813283fd43d1da1a3da8d0824518807123cb47f38701e347e55279145dd1
ARG TARGETARCH
LABEL org.opencontainers.image.title="modelhub-${UNIT}" org.opencontainers.image.version="${RELEASE}"
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin modelhub \
 && mkdir -p /import-work && chown modelhub /import-work
RUN if [ "${UNIT}" = "artifactory_service" ]; then \
      arch="${TARGETARCH:-amd64}"; \
      case "${arch}" in amd64) sha="${JF_SHA256_AMD64}" ;; arm64) sha="${JF_SHA256_ARM64}" ;; \
        *) echo "no pinned JFrog CLI for ${arch}" >&2; exit 1 ;; esac; \
      python -c "import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], sys.argv[2])" \
        "https://releases.jfrog.io/artifactory/jfrog-cli/v2-jf/${JF_VERSION}/jfrog-cli-linux-${arch}/jf" \
        /usr/local/bin/jf \
      && echo "${sha}  /usr/local/bin/jf" | sha256sum -c - \
      && chmod 755 /usr/local/bin/jf; \
    fi
COPY --from=build /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp \
    HF_HOME=/tmp/hf \
    HF_HUB_DISABLE_XET=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    JFROG_CLI_AVOID_NEW_VERSION_WARNING=true \
    JFROG_CLI_REPORT_USAGE=false \
    JFROG_CLI_HOME_DIR=/tmp/.jfrog \
    MODELHUB_PORT=8000
USER 10001
EXPOSE 8000
ENTRYPOINT ["python", "-m"]
