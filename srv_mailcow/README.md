This directory holds the single-container mail server (docker-mailserver) configuration for darkstore.local.

What’s included
- Dockerfile deriving from docker-mailserver, with a wrapper entrypoint that:
  - Disables TLS (lab only) via postfix-main.cf and dovecot.cf overrides.
  - Enables base SEG settings (Rspamd mime type blocking).
  - On first start, generates accounts and stores passwords in config/secrets/generated-passwords.txt, and hashes in postfix-accounts.cf.
- Persistent volumes: mail-data, mail-state, mail-logs, and config under this folder.

Users
- petrovich@darkstore.local
- boss@darkstore.local
- evgen@darkstore.local
- brown.anna@darkstore.local

Passwords
- See: config/secrets/generated-passwords.txt (created at first start).

