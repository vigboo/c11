#!/bin/sh
set -eu

# Human-readable setup for app_nginx container
# - Sets default route via firewall
# - Installs nginx + OpenSSH server
# - Creates users petrovich and ansible with passwords from env
# - Enables password auth in sshd (no PAM on Alpine)
# - Starts sshd (background) and nginx (foreground)

GATEWAY_IP="${GATEWAY_IP}"

# Network route first (before apk fetches)
ip route del default 2>/dev/null || true
ip route add default via "$GATEWAY_IP" || true

# Packages
apk --no-cache add bash nginx openssh iproute2 sudo openssl shadow >/dev/null

# Minimal nginx site
printf 'server { listen 80 default_server; server_name _; root /usr/share/nginx/html; index index.html; location / { try_files $uri $uri/ =404; } }' > /etc/nginx/http.d/zz-serve.conf
rm -f /etc/nginx/http.d/default.conf 2>/dev/null || true

# Разворачиваем sshd + ansible пользователя
chmod +x /usr/local/bin/ansible_agent_deploy.sh
/usr/local/bin/ansible_agent_deploy.sh
/usr/sbin/sshd

# Start services
exec nginx -g 'daemon off;'

