#!/usr/bin/env bash
set -euo pipefail

# Enable IPv4 forwarding (privileged container)
sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true

# Prepare PATH
echo 'export PATH=/usr/sbin:/sbin:$PATH' > /etc/profile.d/00-sbin.sh

# SSH setup for student user
id -u student >/dev/null 2>&1 || adduser -D student
echo "student:${FW_PASSWORD:-Passw0rd!}" | chpasswd
echo 'student ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/90-student && chmod 0440 /etc/sudoers.d/90-student
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

# Ensure default route goes via the uplink (interface with 172.x address)
upline=$(ip -o -4 addr show | awk '/\binet 172\./{print $2, $4; exit}') || true
if [ -n "$upline" ]; then
  intf=$(echo "$upline" | awk '{print $1}')
  ipcidr=$(echo "$upline" | awk '{print $2}')
  ip=$(echo "$ipcidr" | cut -d/ -f1)
  gw=$(echo "$ip" | awk -F. '{printf "%s.%s.%s.1\n", $1,$2,$3}')
  ip route replace default via "$gw" dev "$intf" || true
fi

# Keep running
exec /usr/sbin/sshd -D
