# Secrets Management

> Status: Tool chosen — **SOPS + age**. Day-to-day workflow and rotation policy still being fleshed out.

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

## Chosen approach: SOPS + age

- File-based, encrypted at rest in git → safe for a public repo.
- Works across all three IaC layers:
  - Ansible via `community.sops` collection (decrypts `*.sops.yaml` vars at play time)
  - OpenTofu via the `carlpett/sops` provider
  - Docker / compose via `sops exec-env` or rendered env files at deploy time
- No always-on service to bootstrap from cold — the entire system is recoverable with just the repo + one age private key.
- Master/recovery age key:
  - Primary copy: Proton Pass
  - Offline copy: paper backup in a safe place
- Repo will be public once the lab is live; treated as already public during the build (no plaintext secrets, ever).

## Open questions

- Bootstrap chicken-and-egg: how does the very first Ansible run on a fresh node get the age private key? Likely: `scp` from the admin workstation as part of `bootstrap.md`, then Ansible takes over.
- Rotation policy: cadence and the one-shot re-encryption workflow when the master key is rotated.
- Day-to-day workflow: probably `sops edit secrets/<scope>.yaml` + commit, possibly fronted by a `just` recipe.

## For now

Nothing committed to this repo should contain plaintext credentials. Real secrets land in git only via SOPS-encrypted files; loose `.env` files for early experimentation stay gitignored.
