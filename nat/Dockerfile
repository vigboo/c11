FROM alpine:3.20

RUN apk add --no-cache iptables iproute2 bash tcpdump

COPY start.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/bin/sh", "/entrypoint.sh"]

