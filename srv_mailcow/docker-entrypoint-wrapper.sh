#!/usr/bin/env bash
set -euo pipefail


# Разворачиваем sshd + ansible пользователя
chmod +x /usr/local/bin/ansible_agent_deploy.sh
/usr/local/bin/ansible_agent_deploy.sh
/usr/sbin/sshd

CONF_DIR="/tmp/docker-mailserver"
SECRETS_DIR="$CONF_DIR/secrets"
RSPAMD_DIR="$CONF_DIR/rspamd"

mkdir -p "$CONF_DIR" "$SECRETS_DIR" "$RSPAMD_DIR/override.d"

# Ensure TLS disabled for lab: postfix + dovecot overrides
cat > "$CONF_DIR/postfix-main.cf" << 'EOF'
# Disable TLS (lab/internal only)
smtpd_use_tls = no
smtp_use_tls = no
smtpd_tls_security_level = none
smtp_tls_security_level = none
smtpd_tls_auth_only = no
EOF

cat > "$CONF_DIR/dovecot.cf" << 'EOF'
# Disable TLS for IMAP/POP (lab)
ssl = no
# Allow plaintext auth even without SSL (lab only)
disable_plaintext_auth = no
# Ensure PLAIN/LOGIN mechanisms are enabled
auth_mechanisms = plain login
EOF

# Basic anti-malware/SEG tweaks via Rspamd: block common dangerous extensions
cat > "$RSPAMD_DIR/override.d/mime_types.conf" << 'EOF'
bad_extensions = ["exe", "js", "vbs", "scr", "pif", "bat", "cmd", "com", "jar", "msc", "ps1", "psm1"]; 
bad_files = ["*.exe", "*.js", "*.vbs", "*.scr", "*.pif", "*.bat", "*.cmd", "*.com", "*.jar", "*.msc", "*.ps1", "*.psm1"]; 
EOF

# Provide dummy self-signed certs to satisfy startup checks (TLS will be disabled by overrides)
SSL_DIR="$CONF_DIR/ssl"
CERT="$SSL_DIR/cert.pem"
KEY="$SSL_DIR/key.pem"
mkdir -p "$SSL_DIR"
if [ ! -s "$CERT" ] || [ ! -s "$KEY" ]; then
  openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
    -keyout "$KEY" -out "$CERT" -subj "/CN=mail.darkstore.local" >/dev/null 2>&1 || true
fi

# Initialize domain and accounts only once
ACCOUNTS_CF="$CONF_DIR/postfix-accounts.cf"
PASS_TXT="$SECRETS_DIR/generated-passwords.txt"

if [ ! -s "$ACCOUNTS_CF" ]; then
  domain="darkstore.local"
  declare -A users=(
    ["petrovich"]=""
    ["boss"]=""
    ["trust"]=""
    ["b.anna"]=""
  )

  # Generate simple random passwords (A-Za-z0-9, length 12)
  genpw() { tr -dc 'A-Za-z0-9' </dev/urandom | head -c 12; echo; }

  : > "$PASS_TXT"
  : > "$ACCOUNTS_CF.tmp"

  for u in "${!users[@]}"; do
    pw=$(genpw)
    users[$u]="$pw"
    # Hash with dovecot
    hash=$(doveadm pw -s SHA512-CRYPT -p "$pw")
    echo "$u@$domain:$pw" >> "$PASS_TXT"
    echo "$u@$domain|$hash" >> "$ACCOUNTS_CF.tmp"
  done

  mv "$ACCOUNTS_CF.tmp" "$ACCOUNTS_CF"

  # Postmaster/abuse aliases to boss
  cat > "$CONF_DIR/postfix-virtual.cf" << 'EOF'
postmaster@darkstore.local boss@darkstore.local
abuse@darkstore.local boss@darkstore.local
EOF
fi


exec "$@"
