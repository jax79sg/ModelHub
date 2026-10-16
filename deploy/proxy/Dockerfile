# The entry point: the nginx project's unprivileged image with our routing and TLS settings.
ARG NGINX_IMAGE=nginxinc/nginx-unprivileged:1.27
FROM ${NGINX_IMAGE}
COPY deploy/proxy/nginx.conf /etc/nginx/nginx.conf
