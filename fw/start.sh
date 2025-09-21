#!/usr/bin/env bash
set -euo pipefail

# Enable IPv4 forwarding (privileged container)
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true

# Prepare PATH
echo 'export PATH=/usr/sbin:/sbin:$PATH' > /etc/profile.d/00-sbin.sh

# SSH setup for petrovich (system administrator)
id -u petrovich >/dev/null 2>&1 || adduser -D petrovich
echo "petrovich:${PETROVICH_PASSWORD:-Passw0rd!}" | chpasswd
echo 'petrovich ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/90-petrovich && chmod 0440 /etc/sudoers.d/90-petrovich
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
mkdir -p /run/sshd
ssh-keygen -A

# Load nftables rules. Convert CRLF if mounted from Windows.
if [ -f /etc/nftables.conf ]; then
  tr -d '\r' < /etc/nftables.conf > /tmp/nft.conf
  if ! nft -f /tmp/nft.conf; then
    echo "nftables load failed -> falling back to iptables permissive routing" >&2
    # permissive fallback: allow forward and basic NAT on last iface (uplink)
    iptables -P FORWARD ACCEPT
    iptables -t nat -C POSTROUTING -o eth3 -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -o eth3 -j MASQUERADE
  fi
fi



# Keep running
exec /usr/sbin/sshd -D
