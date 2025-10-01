#!/bin/sh
set -eu

GW=${GATEWAY_IP:-}
PATCH_HELPER=/tmp/patch_default.sh

# Ensure default route follows the provided gateway
ip route del default 2>/dev/null || true
[ -n "$GW" ] && ip route add default via "$GW" || true

cat <<'PATCHSCRIPT' > "$PATCH_HELPER"
#!/bin/sh
while [ ! -f /etc/nginx/default-server-http.conf ]; do
  sleep 2
done
python3 - <<'PYHELP'
from pathlib import Path
path = Path("/etc/nginx/default-server-http.conf")
text = path.read_text()
if 'proxy_pass http://192.168.0.10;' in text:
    raise SystemExit(1)
lines = text.splitlines()
start = None
for idx, line in enumerate(lines):
    if line.lstrip().startswith('location / '):
        start = idx
        break
if start is None:
    raise SystemExit(1)
depth = 0
end = None
for idx in range(start, len(lines)):
    depth += lines[idx].count('{')
    depth -= lines[idx].count('}')
    if depth == 0:
        end = idx
        break
if end is None:
    raise SystemExit(1)
cur = chr(36)
new_block = [
    "	location / {",
    f"		proxy_set_header Host {cur}host;",
    f"		proxy_set_header X-Real-IP {cur}remote_addr;",
    f"		proxy_set_header X-Forwarded-For {cur}proxy_add_x_forwarded_for;",
    f"		proxy_set_header X-Forwarded-Proto {cur}scheme;",
    "		proxy_http_version 1.1;",
    "		proxy_set_header Connection "";",
    "		proxy_pass http://192.168.0.10;",
    "	}"
]
updated = lines[:start] + new_block + lines[end + 1:]
path.write_text("
".join(updated) + "
")
PYHELP
if [ $? -eq 0 ] && [ -f /var/run/bunkerweb/nginx.pid ]; then
  nginx -s reload >/dev/null 2>&1 || true
fi
PATCHSCRIPT
chmod +x "$PATCH_HELPER"
nohup /bin/sh "$PATCH_HELPER" >/dev/null 2>&1 &

if [ -x /usr/share/bunkerweb/entrypoint.sh ]; then
  exec /usr/share/bunkerweb/entrypoint.sh "$@"
fi

echo "Error: bunkerweb entrypoint not found" >&2
exit 127
