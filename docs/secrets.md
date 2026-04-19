# Secrets Management

> Status: Work in progress. No tool is chosen yet. This file just scopes the problem so a decision can be made later.

## What counts as a secret here

Roughly anything that should never land in git in plaintext:

- SSH private keys, root passwords, sudo passwords
- API tokens (cloud provider, DNS, Restic repo password, registry auth, ...)
- App environment variables (database passwords, OIDC client secrets, SMTP creds, VPN credentials, ...)
- TLS certificates / private keys (if not fully managed by Caddy)
- Backup encryption keys (Restic repo key, age keys, ...)
- Authentik signing keys, session secrets, ...
- Wake-on-LAN / iLO credentials

## What this system needs to do

- Be safe to commit to this (potentially public?) repo.
- Be usable by all three layers: Ansible (OS config), OpenTofu (Incus provisioning), Docker Compose (app env).
- Survive a full rebuild from a fresh machine with nothing but the git repo + one recovery key.
- Not require me to remember a dozen different passphrases.
- Not require running a separate always-on service just to boot the rest of the lab (chicken-and-egg problem).

## Candidate approaches (not ranked, not chosen)

- File-based, encrypted in git: SOPS + age, git-crypt, ansible-vault, ...
- External secrets store: HashiCorp Vault, Infisical, Bitwarden/Vaultwarden + CLI, ...
- Hybrid: small master key in a password manager, bulk secrets encrypted in git and decrypted at deploy time.
- Plain `.env` files kept out of git + a separate encrypted offline backup.

Each has trade-offs around bootstrap complexity, multi-tool integration, and key rotation. To be evaluated.

## Open questions

- Is this repo going to be public, private, or private-with-some-public-parts? (Drives how strict the "safe to commit" bar is.)
- Where does the root/recovery key live? (Password manager? Offline paper backup? Hardware token?)
- How are secrets rotated, and how often?
- How do new secrets get added day-to-day — is there a single command or workflow?

## For now

Until a tool is picked, secrets should stay out of git entirely (local `.env` files, ignored paths). Nothing committed here should contain real credentials.
