#!/usr/bin/env bash
set -euo pipefail

# Create student user if missing
id -u student >/dev/null 2>&1 || adduser -D student
echo "student:${APP2_PASSWORD:-Passw0rd!}" | chpasswd
# Allow passwordless sudo for student (Alpine)
grep -q '^#includedir /etc/sudoers.d' /etc/sudoers || echo '#includedir /etc/sudoers.d' >> /etc/sudoers
mkdir -p /etc/sudoers.d && echo 'student ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/90-student && chmod 0440 /etc/sudoers.d/90-student

# Create ansible user with sudo (Alpine) for Ansible management
id -u ansible >/dev/null 2>&1 || adduser -D ansible
echo "ansible:${ANSIBLE_PASSWORD:-${APP2_PASSWORD:-Passw0rd!}}" | chpasswd
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
