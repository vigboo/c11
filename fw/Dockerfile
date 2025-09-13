FROM alpine:3.20

ENV TZ=Etc/UTC

RUN apk add --no-cache nftables iproute2 iptables openssh sudo bash

COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

CMD ["/usr/local/bin/start.sh"]
