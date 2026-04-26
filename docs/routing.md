# Routing and TLS

Status: Caddy chosen.

## Decisions

Decision | Choice
--- | ---
Reverse proxy | Caddy
Deployment | Docker Compose on the edge node
Config source | Caddyfile in Git
Public domain | `{{ homelab_domain }}`
DNS provider | Cloudflare, DNS-only
TLS | Let's Encrypt DNS-01 via Cloudflare
Cloudflare proxy | Disabled
Internal DNS | AdGuard split-horizon override to edge

## Model

All HTTP/HTTPS traffic enters through the edge node at `10.0.0.10`.

External flow:

1. Public DNS resolves `service.{{ homelab_domain }}` to the home public IP.
2. Livebox forwards `80/tcp` and `443/tcp` to `10.0.0.10`.
3. Caddy routes by hostname to private upstreams.

Internal flow:

1. AdGuard resolves `service.{{ homelab_domain }}` to `10.0.0.10`.
2. Caddy receives the same hostname.
3. Caddy routes to the same private upstream.

Caddy does not need a catch-all `*.{{ homelab_domain }}` site block. Routing should be explicit per service.

## TLS Strategy

Use Let's Encrypt DNS-01 through Cloudflare.

This requires:

- Caddy build with the Cloudflare DNS plugin
- Cloudflare API token from SOPS
- per-host certificates by default
- wildcard certificate for `*.{{ homelab_domain }}` only if explicitly configured

Routes stay explicit per hostname. Caddy does not need wildcard routing unless wildcard certificate management is deliberately enabled.

`{{ secondary_domain }}` is not used until it has a concrete purpose.

## Exposure Model

Exposure | Meaning
--- | ---
Public | Reachable from the internet through Caddy
Private | Only reachable from LAN/VPN source ranges

Admin and infrastructure services default to private.

Forward auth is provided by Authentik and is applied per service. It should not be global by default because some apps have good native auth and some services need special handling.

## Non-HTTP Traffic

Caddy is only for HTTP/HTTPS.

For TCP/UDP services, public ports enter through the edge node first when practical, then forward/NAT to the service host. Direct forwarding to compute is an exception.
