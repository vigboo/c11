#!/bin/sh
set -eu

GW=${GATEWAY_IP}

ip route del default 2>/dev/null || true
ip route add default via "$GW" || true

exec coredns -conf /etc/coredns/Corefile
