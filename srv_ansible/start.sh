#!/usr/bin/env bash
set -euo pipefail

# Ensure petrovich exists and set password
if ! id -u petrovich >/dev/null 2>&1; then
  useradd -m -s /bin/bash petrovich || true
fi
echo "petrovich:${PETROVICH_PASSWORD}" | chpasswd
echo 'petrovich ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/90-petrovich
chmod 0440 /etc/sudoers.d/90-petrovich

# Ensure local ansible user (useful for self-management)
if ! id -u ansible >/dev/null 2>&1; then
  useradd -m -s /bin/bash ansible || true
fi
echo "ansible:${ANSIBLE_PASSWORD}" | chpasswd
echo 'ansible ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/91-ansible
chmod 0440 /etc/sudoers.d/91-ansible

# Default route via firewall
GATEWAY_IP=${GATEWAY_IP}
ip route del default || true
ip route add default via "$GATEWAY_IP" || true

# SSHD setup
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
mkdir -p /run/sshd
ssh-keygen -A

# Keep running: sshd in foreground
exec /usr/sbin/sshd -D
