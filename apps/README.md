# apps/ — Docker Compose stacks

One directory per stack, grouped by node. Secrets are never stored here in
plaintext: `.env` files are rendered at deploy time from `secrets/*.sops.env`
and are gitignored.

| Stack | Node | Purpose |
| --- | --- | --- |
| `edge/caddy` | edge | Ingress, TLS (DNS-01 via Cloudflare plugin, custom build) |
| `edge/adguard` | edge | DNS + DHCP (host networking) |
| `edge/ddns` | edge | Cloudflare dynamic DNS for the home IP |

Planned next: `edge/authentik`, `edge/dockge`, then the compute stacks
(see `docs/services.md`).

Configs follow each project's official documentation example, modified
minimally — when touching a stack, re-check upstream docs first.

Image tags use explicit Renovate-managed versions. Avoid `latest`: Renovate is
the version update mechanism.

## Edge first-deploy notes

1. Render each stack's `.env` from SOPS before `docker compose up -d`, e.g.
   `sops decrypt secrets/edge-caddy.sops.env > apps/edge/caddy/.env`.
2. Deploy order: `caddy` + `ddns` first (gives a real cert on `dns.{{ homelab_domain }}`),
   then `adguard`.
3. AdGuard runs host-networked, so during its setup wizard set the **admin web
   UI to port 3000** — Caddy owns `80/443` on the host. The Caddyfile proxies
   `dns.{{ homelab_domain }} → 10.0.0.10:3000`.
4. AdGuard binds `:53`. Confirm nothing else holds it first
   (`ss -lunp | grep :53`); on a minimal Debian install systemd-resolved is not
   enabled, but if present, disable its stub listener.
5. Bridged edge services added later (Authentik, Dockge) must join a shared
   external network with Caddy — see `docs/routing.md`.
