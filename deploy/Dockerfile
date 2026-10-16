# One image recipe for the three Python services (portal, catalog, artifactory-service).
# Build with: docker build -f deploy/Dockerfile --build-arg UNIT=catalog -t modelhub/catalog:<release> .
# The Artifactory stand-in and the test helpers are never installed here (checked in CI).
ARG PYTHON_IMAGE=python:3.12-slim

FROM ${PYTHON_IMAGE} AS build
ARG UNIT
WORKDIR /src
COPY pyproject.toml README.md ./
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
 && /opt/venv/bin/pip install --no-cache-dir ${PKGS}

FROM ${PYTHON_IMAGE}
ARG UNIT
ARG RELEASE=dev
LABEL org.opencontainers.image.title="modelhub-${UNIT}" org.opencontainers.image.version="${RELEASE}"
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin modelhub \
 && mkdir -p /import-work && chown modelhub /import-work
COPY --from=build /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp \
    HF_HOME=/tmp/hf \
    MODELHUB_PORT=8000
USER 10001
EXPOSE 8000
ENTRYPOINT ["python", "-m"]
