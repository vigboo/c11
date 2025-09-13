#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export ANSIBLE_HOST_KEY_CHECKING=False
ansible-playbook -i inventory/hosts.ini playbooks/monitor.yml "$@"

