#!/usr/bin/env bash
set -euo pipefail

# Create petrovich user if missing
id -u petrovich >/dev/null 2>&1 || adduser -D petrovich
echo "petrovich:${PETROVICH_PASSWORD}" | chpasswd
# Allow passwordless sudo for petrovich (Alpine)
grep -q '^#includedir /etc/sudoers.d' /etc/sudoers || echo '#includedir /etc/sudoers.d' >> /etc/sudoers
mkdir -p /etc/sudoers.d && echo 'petrovich ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/90-petrovich && chmod 0440 /etc/sudoers.d/90-petrovich

# Create ansible user with sudo (Alpine) for Ansible management
id -u ansible >/dev/null 2>&1 || adduser -D ansible
echo "ansible:${ANSIBLE_PASSWORD}" | chpasswd
echo 'ansible ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/91-ansible && chmod 0440 /etc/sudoers.d/91-ansible

# SSH config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
mkdir -p /run/sshd
ssh-keygen -A

# Default route via firewall
GATEWAY_IP=${GATEWAY_IP:-192.168.1.1}
ip route del default || true
ip route add default via "$GATEWAY_IP" || true

exec /usr/sbin/sshd -D
