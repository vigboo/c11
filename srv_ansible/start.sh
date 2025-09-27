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

cat > /etc/cron.d/ansible_runner << EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
HOME=/root
# Propagate env for sync and ansible
ANSIBLE_PASSWORD=${ANSIBLE_PASSWORD}
SAMBA_SERVER=${SAMBA_SERVER:-192.168.0.22}
SAMBA_SHARE_NAME=${SAMBA_SHARE_NAME:-Share}
WORKGROUP=${WORKGROUP:-WORKGROUP}
REMOTE_PATH=${REMOTE_PATH:-it}
LOCAL_PATH=${LOCAL_PATH:-/workspace}
SAMBA_USER=${SAMBA_USER}
SAMBA_PASSWORD=${SAMBA_PASSWORD}
SMB_DEBUGLEVEL=${SMB_DEBUGLEVEL:-2}
SMB_PROTOCOL=${SMB_PROTOCOL:-SMB3}
LOG_FILE=/var/log/get_ansible_workspace.log
ANSIBLE_LOG_FILE=/var/log/ansible_runner.log
* * * * * root flock -n /var/run/ansible-workspace.lock -c "/usr/bin/env python3 /usr/local/bin/ansible_sync.py"
EOF
chmod 0644 /etc/cron.d/ansible_runner
service cron restart || service cron start || true

# Keep running: sshd in foreground
exec /usr/sbin/sshd -D
