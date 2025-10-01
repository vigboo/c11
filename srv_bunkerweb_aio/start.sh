#!/bin/sh
set -eu

GW=${GATEWAY_IP:-}


if [ -x /entrypoint.sh ]; then
  exec /entrypoint.sh "$@"
fi

if [ -x /usr/share/bunkerweb/entrypoint.sh ]; then
  exec /usr/share/bunkerweb/entrypoint.sh "$@"
fi

echo "Error: bunkerweb entrypoint not found" >&2
exit 127
