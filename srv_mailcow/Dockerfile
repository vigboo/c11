FROM ghcr.io/docker-mailserver/docker-mailserver:latest
COPY ./amavis/50-user /etc/amavis/conf.d/50-user
RUN chown root:root /etc/amavis/conf.d/50-user && chmod 0644 /etc/amavis/conf.d/50-user
