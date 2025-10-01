FROM alpine:3.20

RUN apk add --no-cache coredns iproute2

COPY start.sh /start.sh
RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]
