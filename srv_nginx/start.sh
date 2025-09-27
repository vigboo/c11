#!/bin/sh
set -eu

# Human-readable setup for app_nginx container
# - Sets default route via firewall
# - Installs nginx + OpenSSH server
# - Creates users petrovich and ansible with passwords from env
# - Enables password auth in sshd (no PAM on Alpine)
# - Starts sshd (background) and nginx (foreground)

GATEWAY_IP="${GATEWAY_IP:-192.168.2.254}"

# Network route first (before apk fetches)
ip route del default 2>/dev/null || true
ip route add default via "$GATEWAY_IP" || true

# Packages
apk add --no-cache \
  nginx openssh iproute2 sudo openssl shadow >/dev/null

# Users: petrovich
if ! id -u petrovich >/dev/null 2>&1; then
  adduser -D petrovich
fi
if [ -n "${PETROVICH_PASSWORD:-}" ]; then
  PHASH=$(openssl passwd -6 "${PETROVICH_PASSWORD}")
  usermod -p "$PHASH" petrovich
fi
mkdir -p /etc/sudoers.d
echo 'petrovich ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/90-petrovich
chmod 0440 /etc/sudoers.d/90-petrovich

# Users: ansible
if ! id -u ansible >/dev/null 2>&1; then
  adduser -D ansible
fi
APW="${ANSIBLE_PASSWORD:-${APP1_PASSWORD:-Passw0rd!}}"
AHASH=$(openssl passwd -6 "$APW")
usermod -p "$AHASH" ansible
echo 'ansible ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/91-ansible
chmod 0440 /etc/sudoers.d/91-ansible

# SSH server config (no PAM on Alpine)
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
grep -q '^KbdInteractiveAuthentication' /etc/ssh/sshd_config || echo 'KbdInteractiveAuthentication no' >> /etc/ssh/sshd_config
sed -i '/^UsePAM/d' /etc/ssh/sshd_config

mkdir -p /run/sshd /run/nginx
ssh-keygen -A >/dev/null 2>&1 || true

# Minimal nginx site
printf 'server { listen 80 default_server; server_name _; root /usr/share/nginx/html; index index.html; location / { try_files $uri $uri/ =404; } }' > /etc/nginx/http.d/zz-serve.conf
rm -f /etc/nginx/http.d/default.conf 2>/dev/null || true

# Start services
/usr/sbin/sshd
exec nginx -g 'daemon off;'

