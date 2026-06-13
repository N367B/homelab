# Secrets

All files here are SOPS-encrypted with age (see `/.sops.yaml`). Nothing in this
directory is ever committed in plaintext — the repo is treated as public.

## Workflow

Add or edit a secret (creates the file encrypted if it does not exist):

```sh
sops edit secrets/edge.sops.yaml
```

Use from each layer:

- Ansible: `community.sops` collection loads `*.sops.yaml` vars at play time
- OpenTofu: `carlpett/sops` provider
- Docker Compose: render an env file at deploy time, e.g.
  `sops decrypt secrets/edge-caddy.sops.env > apps/edge/caddy/.env` (the `.env` is gitignored)

## Planned scopes

| File | Contents |
| --- | --- |
| `edge.sops.yaml` | Ansible vars for the edge node |
| `edge-caddy.sops.env` | `CF_API_TOKEN` for TLS DNS-01 (scopes: Zone.Zone:Read + Zone.DNS:Edit) |
| `edge-ddns.sops.env` | `CLOUDFLARE_API_TOKEN` for DDNS (separate token, same scopes, revocable alone) |
| `backup.sops.yaml` | Restic repo password, B2 credentials |
