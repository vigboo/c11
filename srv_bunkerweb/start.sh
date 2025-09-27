#!/bin/sh
set -eu

# Ensure default route follows the firewall IP provided via $GATEWAY_IP
# Network route first (before apk fetches)
ip route del default 2>/dev/null || true
ip route add default via "$GATEWAY_IP" || true

# Hand back to the original bunkerweb entrypoint
if [ -x /usr/share/bunkerweb/entrypoint.sh ]; then
  exec /usr/share/bunkerweb/entrypoint.sh "$@"
fi

echo "Error: bunkerweb entrypoint not found" >&2
exit 127
