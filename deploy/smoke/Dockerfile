# The smoke-test image: the stand-ins for Keycloak and Artifactory, and the driver that plays a
# browser and an import computer. It is for CI only and is never part of a server pack.
FROM python:3.12-slim
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
COPY server/testkit ./server/testkit
COPY server/stand_in ./server/stand_in
RUN pip install --no-cache-dir . ./server/testkit ./server/stand_in
COPY deploy/smoke /smoke
ENV PYTHONUNBUFFERED=1 HF_HUB_DISABLE_XET=1 HF_HUB_DISABLE_TELEMETRY=1
