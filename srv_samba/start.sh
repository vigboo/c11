#!/usr/bin/env bash
set -euo pipefail

# Defaults
SAMBA_USER=${SAMBA_USER:-petrovich}
SAMBA_PASSWORD=${SAMBA_PASSWORD:-Passw0rd!}
SAMBA_SHARE_NAME=${SAMBA_SHARE_NAME:-Share}
SAMBA_SHARE_PATH=${SAMBA_SHARE_PATH:-/share}
WORKGROUP=${WORKGROUP:-WORKGROUP}

# Default route via firewall (optional)
GATEWAY_IP=${GATEWAY_IP:-192.168.0.1}
ip route del default || true
ip route add default via "$GATEWAY_IP" || true

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

# Create local users (system + ansible)
if ! id -u "$SAMBA_USER" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$SAMBA_USER" || true
fi
echo "$SAMBA_USER:$SAMBA_PASSWORD" | chpasswd
echo "$SAMBA_USER ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/90-$SAMBA_USER
chmod 0440 /etc/sudoers.d/90-$SAMBA_USER

if ! id -u ansible >/dev/null 2>&1; then
  useradd -m -s /bin/bash ansible || true
fi
echo "ansible:${ANSIBLE_PASSWORD:-$SAMBA_PASSWORD}" | chpasswd
echo 'ansible ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/91-ansible
chmod 0440 /etc/sudoers.d/91-ansible

# Prepare share and sample content
mkdir -p "$SAMBA_SHARE_PATH"
for d in mems managers buh it; do
  mkdir -p "$SAMBA_SHARE_PATH/$d"
  if [ ! -f "$SAMBA_SHARE_PATH/$d/readme.rtf" ]; then
    cat > "$SAMBA_SHARE_PATH/$d/readme.rtf" <<'RTF'
{\rtf1\ansi\deff0{\fonttbl{\f0 Arial;}}\f0\fs22
This is a sample RTF file for the share.
}
RTF
  fi
done

add_png() {
  name="$1"
  path="$SAMBA_SHARE_PATH/mems/$name"
  [ -f "$path" ] && return 0
  cat > "$path.b64" << 'B64'
iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=
B64
  base64 -d "$path.b64" > "$path" 2>/dev/null || true
  rm -f "$path.b64"
}
add_png distracted_boyfriend.png
add_png this_is_fine.png
add_png is_it_bug_or_feature.png
add_png programmer_humor.png
add_png stackoverflow.png

chmod -R 0777 "$SAMBA_SHARE_PATH" || true

# Samba configuration
mkdir -p /var/log/samba
cat > /etc/samba/smb.conf <<EOF
[global]
   workgroup = $WORKGROUP
   server role = standalone server
   map to guest = Bad User
   usershare allow guests = yes
   dns proxy = no
   log file = /var/log/samba/log.%m
   max log size = 50
   load printers = no
   printing = bsd
   disable spoolss = yes

[$SAMBA_SHARE_NAME]
   path = $SAMBA_SHARE_PATH
   browseable = yes
   read only = no
   guest ok = yes
   create mask = 0666
   directory mask = 0775
EOF

# Create Samba user (requires system account to exist)
printf '%s\n%s\n' "$SAMBA_PASSWORD" "$SAMBA_PASSWORD" | smbpasswd -s -a "$SAMBA_USER" || true

# Start services
/usr/sbin/sshd
ionice -c 3 nmbd -D || true
# Start smbd in foreground (-F); '-S' is not supported on Debian/Ubuntu smbd
exec ionice -c 3 smbd -F --no-process-group </dev/null
