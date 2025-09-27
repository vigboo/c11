#!/usr/bin/env bash
set -euo pipefail

# Ensure safe working dir for cron (workspace may be wiped by sync)
cd / || exit 1
export HOME=/root
export ANSIBLE_HOST_KEY_CHECKING=False

INVENTORY=/workspace/ansible/inventory/hosts.ini
PLAYBOOK_DIR=/workspace/ansible/playbooks
LOG=/var/log/ansible_runner.log

mkdir -p "$(dirname "$LOG")"
echo "ANSIBLE_PASSWORD is: $ANSIBLE_PASSWORD"

# Skip if inventory not yet synced
[ -f "$INVENTORY" ] || exit 0

(
  date '+%F %T'
  ansible-playbook -i "$INVENTORY" "$PLAYBOOK_DIR/healthcheck.yml" -u root --extra-vars "ansible_password='$ANSIBLE_PASSWORD'" || true
  ansible-playbook -i "$INVENTORY" "$PLAYBOOK_DIR/stub.yml" -u root --extra-vars "ansible_password='$ANSIBLE_PASSWORD'" || true
) >> "$LOG" 2>&1
