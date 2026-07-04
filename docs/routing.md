# Routing and TLS

Status: Caddy chosen.

## Decisions

| Decision         | Choice                                 |
| ---------------- | -------------------------------------- |
| Reverse proxy    | Caddy                                  |
| Deployment       | Docker Compose on the edge node        |
| Config source    | Caddyfile in Git                       |
| Public domain    | `{{ homelab_domain }}`                 |
| DNS provider     | Cloudflare, DNS-only                   |
| TLS              | Let's Encrypt DNS-01 via Cloudflare    |
| Cloudflare proxy | Disabled                               |
| Internal DNS     | AdGuard split-horizon override to edge |

## Model

All HTTP/HTTPS traffic enters through the edge node at `10.0.0.10`.

External flow:

1. Public DNS resolves `service.{{ homelab_domain }}` to the home public IP.
2. Livebox forwards `80/tcp`, `443/tcp`, and `443/udp` to `10.0.0.10`.
3. Caddy routes by hostname to private upstreams.

Internal flow:

1. AdGuard resolves `service.{{ homelab_domain }}` to `10.0.0.10`.
2. Caddy receives the same hostname.
3. Caddy routes to the same private upstream.

Caddy does not need a catch-all `*.{{ homelab_domain }}` site block. Routing should be explicit per service.

HTTP/3 is supported externally. Caddy publishes `443/udp`, the edge firewall allows `443/udp`, and the Livebox should forward UDP 443 alongside TCP 443. Clients that cannot use QUIC fall back to HTTP/2 over TCP.

## How Caddy Reaches Upstreams

Each app stack is its own Docker Compose project. On the edge node, Caddy uses host networking so it can bind public ingress ports directly and reach local backends over loopback.

- Host-networked services (AdGuard, Home Assistant) are reached over loopback, e.g. `reverse_proxy 127.0.0.1:3000`. Their raw service ports are not opened in the host firewall.
- Bridged services on the same node, such as Authentik or Dockge, should bind only to loopback when Caddy needs to reach them. Example: `127.0.0.1:9000:9000`, then Caddy proxies to `127.0.0.1:9000`.
- Services on the compute node are reached by routed IP (`10.10.40.x:port`).

## Backend Port Policy

Only Caddy-facing ingress ports are user-facing: `80/tcp`, `443/tcp`, and `443/udp` on the edge node. Raw application ports are backend transport only.

- Edge-local bridged Docker services bind host ports only on `127.0.0.1` when Caddy needs to reach them.
- Edge-local host-networked services are reached through `127.0.0.1:<port>` because Caddy also uses host networking.
- Compute services are reached from edge Caddy over private IPs. The compute host firewall should allow those backend ports only from `10.0.0.10`.
- Admin services still require an exposure policy at Caddy (`private_only`, Authentik forward-auth, or native auth), even when their raw ports are blocked.

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

| Exposure | Meaning                                   |
| -------- | ----------------------------------------- |
| Public   | Reachable from the internet through Caddy |
| Private  | Only reachable from LAN/VPN source ranges |

Admin and infrastructure services default to private.

Forward auth is provided by Authentik and is applied per service. It should not be global by default because some apps have good native auth and some services need special handling.

## Non-HTTP Traffic

Caddy is only for HTTP/HTTPS.

For TCP/UDP services, public ports enter through the edge node first when practical, then forward/NAT to the service host. Direct forwarding to compute is an exception.
