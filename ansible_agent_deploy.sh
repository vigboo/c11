#!/bin/bash

#Скрипт выполняет первичную конфиуграцию SSHD и создает пользователя для ansible
set -euo pipefail

ANSIBLE_PASSWORD=${ANSIBLE_PASSWORD}

# SSH setup (avoid noisy errors if config dir missing)
mkdir -p /etc/ssh /run/sshd
if [ ! -f /etc/ssh/sshd_config ]; then
  cat > /etc/ssh/sshd_config <<'EOF'
Port 22
Protocol 2
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key
PasswordAuthentication yes
PermitRootLogin no
UsePAM yes
Subsystem sftp /usr/lib/openssh/sftp-server
EOF
fi
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config || true
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config || true
ssh-keygen -A >/dev/null 2>&1 || true

if ! id -u ansible >/dev/null 2>&1; then
  useradd -m -s /bin/bash ansible || true
fi
echo "ansible:${ANSIBLE_PASSWORD}" | chpasswd
echo 'ansible ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/91-ansible
chmod 0440 /etc/sudoers.d/91-ansible

mkdir -p /run/sshd
chmod 755 /run/sshd

