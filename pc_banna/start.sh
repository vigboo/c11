#!/bin/sh
set -eu

# Adjust default route via firewall
GATEWAY_IP=${GATEWAY_IP}
ip route del default || true
ip route add default via "$GATEWAY_IP" || true

chmod +x /usr/local/bin/mounted.sh
/usr/local/bin/mounted.sh

# Keep container alive
tail -f /dev/null

