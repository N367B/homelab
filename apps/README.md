# apps/ — Docker Compose stacks

One directory per stack, grouped by node. Secrets are never stored here in
plaintext: `.env` files are rendered at deploy time from `secrets/*.sops.env`
and are gitignored.

| Stack | Node | Purpose |
| --- | --- | --- |
| `edge/caddy` | edge | Ingress, TLS (DNS-01 via Cloudflare plugin, custom build) |
| `edge/adguard` | edge | DNS + DHCP (host networking) |
| `edge/ddns` | edge | Cloudflare dynamic DNS for the home IP |
| `edge/authentik` | edge | Identity provider (OIDC + forward-auth); postgresql + server + worker |

Caddy and Authentik share the external `edge` Docker network (created by the
role from `compose_networks`) so Caddy resolves `authentik:9000` by name.

Planned next: `edge/dockge`, then the compute stacks (see `docs/services.md`).

Configs follow each project's official documentation example, modified
minimally — when touching a stack, re-check upstream docs first.

Image tags use explicit Renovate-managed versions. Avoid `latest`: Renovate is
the version update mechanism.

## Deploying

Stacks are deployed by the `compose_stacks` Ansible role (driven by the
`compose_stacks` list in `configure/group_vars/`), not by hand. For each stack
it copies the files to `/opt/stacks/<name>/`, renders `.env` from the SOPS
secret (decrypted on the controller — the age key never reaches the node), and
runs `docker compose up`. So a deploy is just:

```sh
cd configure && ansible-playbook site.yml --limit edge
```

Caddy is built from its Dockerfile on first deploy (`build: policy`). After a
Renovate bump to its base image, rebuild explicitly:
`docker compose -f /opt/stacks/caddy/compose.yaml build` then re-run the play.

### First-deploy notes

1. **Caddy** provisions the `dns.{{ homelab_domain }}` cert via DNS-01 on startup — watch
   `docker compose logs caddy` for issuance (the real test of the Cloudflare
   token). It 502s until AdGuard is up; that is expected.
2. **AdGuard** runs host-networked. The role starts the container, but the
   first-run app config is a one-time manual step: browse to
   `http://10.0.0.10:3000` and set the **admin web UI to port 3000** (Caddy owns
   `80/443`). Confirm nothing else holds `:53` first (`ss -lunp | grep :53`); on
   a minimal Debian install systemd-resolved is not enabled.
3. Bridged edge services added later (Authentik, Dockge) must join a shared
   external network with Caddy — see `docs/routing.md`.

Manual `sops decrypt … > .env && docker compose up -d` still works for
one-off debugging, but the role is the source of truth.
