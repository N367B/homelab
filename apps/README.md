# apps/ Docker Compose stacks

One directory per stack, grouped by node. Secrets are never stored here in plaintext: `.env` files are rendered at deploy time from `secrets/*.sops.env` and are gitignored.

| Stack | Node | Purpose |
| --- | --- | --- |
| `edge/caddy` | edge | Ingress, TLS (DNS-01 via Cloudflare plugin, custom build) |
| `edge/adguard` | edge | DNS (host networking). DHCP stays on the Freebox |
| `edge/ddns` | edge | Cloudflare dynamic DNS for the home IP |
| `edge/authentik` | edge | Identity provider with OIDC, backed by postgresql + server + worker |
| `edge/homeassistant` | edge | Home Assistant core, host-networked for local integrations |

Caddy runs host-networked and reaches the other stacks over loopback: Authentik on `127.0.0.1:9000`, Home Assistant on `:8123`, AdGuard on `127.0.0.1:3000`.

Planned next: edge management tooling, then the compute stacks (see `docs/services.md`).

Configs follow each project's official documentation example with minimal changes. When touching a stack, re-check upstream docs first.

Image tags use explicit Renovate-managed versions. Avoid `latest`: Renovate is the version update mechanism.

## Deploying

Stacks are deployed by the `compose_stacks` Ansible role, driven by the `compose_stacks` list in `configure/group_vars/`, not by hand. For each stack it copies the files to `/opt/stacks/<name>/`, renders `.env` from the SOPS secret, decrypts on the controller so the age key never reaches the node, and runs `docker compose up`. A deploy is just:

```sh
cd configure && ansible-playbook site.yml --limit edge
```

Caddy is built from its Dockerfile on first deploy (`build: policy`). After a Renovate bump to its base image, rebuild explicitly: `docker compose -f /opt/stacks/caddy/compose.yaml build` then re-run the play.

### First-deploy notes

1. Caddy provisions certificates via DNS-01 on startup. Watch `docker compose logs caddy` for issuance, which is the real test of the Cloudflare token. It returns 502 until AdGuard is up, which is expected.
2. AdGuard runs host-networked and its config is rendered by Ansible from `apps/edge/adguard/AdGuardHome.yaml.j2`, so there is no first-run wizard. Its web UI is reached through Caddy at `dns.<domain>` from the private ranges; port 3000 is closed to the LAN by the edge firewall. Confirm nothing else holds `:53` first with `ss -lunp | grep :53`. On a minimal Debian install, systemd-resolved is not enabled.
3. Bridged edge services added later must join a shared external network with Caddy. See `docs/routing.md`.

Manual `sops decrypt … > .env && docker compose up -d` still works for one-off debugging, but normal deploys should go through Ansible.
