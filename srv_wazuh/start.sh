#!/usr/bin/env bash
set -euo pipefail

WAZUH_PASSWORD=${WAZUH_PASSWORD:-Passw0rd!}

# Set password for student
echo "student:${WAZUH_PASSWORD}" | chpasswd

# Ensure ansible user with sudo (NOPASSWD)
if ! id -u ansible >/dev/null 2>&1; then
  useradd -m -s /bin/bash ansible || true
fi
echo "ansible:${ANSIBLE_PASSWORD:-${WAZUH_PASSWORD:-Passw0rd!}}" | chpasswd
echo 'ansible ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/91-ansible
chmod 0440 /etc/sudoers.d/91-ansible

# Default route via firewall
GATEWAY_IP=${GATEWAY_IP:-192.168.0.1}
ip route del default || true
ip route add default via "$GATEWAY_IP" || true

# SSHD setup
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
mkdir -p /run/sshd
ssh-keygen -A

exec /usr/sbin/sshd -D
