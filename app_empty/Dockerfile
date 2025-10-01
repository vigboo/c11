FROM alpine:3.20

RUN apk add --no-cache openssh iproute2 curl bash sudo tcpdump

COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

CMD ["/usr/local/bin/start.sh"]
