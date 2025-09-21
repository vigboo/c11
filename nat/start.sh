#!/bin/sh
set -eu

# Enable forwarding
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true

# Load iptables rules if present
if [ -s /etc/iptables/rules.v4 ]; then
  iptables-restore -n < /etc/iptables/rules.v4 || true
fi

# Keep container alive
tail -f /dev/null

