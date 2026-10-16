# The entry point: the nginx project's unprivileged image with our routing and TLS settings.
ARG NGINX_IMAGE=nginxinc/nginx-unprivileged:1.27
FROM ${NGINX_IMAGE}
# Take the operating-system fixes released since the base image was built (the scan in CI
# fails on a critical finding that has a fix), then go back to the image's non-root user.
USER root
RUN apt-get update \
 && apt-get -y --no-install-recommends upgrade \
 && rm -rf /var/lib/apt/lists/*
USER 101
COPY deploy/proxy/nginx.conf /etc/nginx/nginx.conf
