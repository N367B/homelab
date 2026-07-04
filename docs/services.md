# Homelab Services and Routing Directory

This is the working cheat sheet for internal ports, external domains, and authentication policies. All ports, domains, and auth policies can change during the build.

Many services will be added later. Only the main ones are listed for now.

## Exposure Legend

| Exposure | Meaning |
| --- | --- |
| Public | Reachable from the internet through Caddy |
| Internal | LAN/VPN only. The domain resolves only via AdGuard split-horizon, with no public DNS record. Caddy refuses non-private source ranges |

Default policy: family-facing apps may be Public. Admin and infrastructure tools are Internal. Public exposure must be deliberate.

## Edge and Core Infrastructure (Server 2 - AM06 Pro)

These services run 24/7 on the edge node and handle network ingress, identity, and DNS.

| Service Name | Internal Port | Domain | Exposure | Auth Provider | Notes |
| --- | --- | --- | --- | --- | --- |
| Caddy | 80, 443 | - | - | - | Master ingress proxy |
| Authentik | 9000 | `auth.{{ homelab_domain }}` | Public | Native | SSO Provider (must be public for OIDC redirects from outside) |
| AdGuard Home | 3000 | `dns.{{ homelab_domain }}` | Internal | Authentik | Internal DNS and DHCP |
| Dockge (Edge) | 5001 | `edge.{{ homelab_domain }}` | Internal | Authentik | Manages Server 2 stacks |

## Media Stack (Server 1 - ML350 Gen9)

These services run on the main compute node and mount the bulk ZFS pool.

| Service Name | Internal Port | Domain | Exposure | Auth Provider | Notes |
| --- | --- | --- | --- | --- | --- |
| Jellyfin | 8096 | `media.{{ homelab_domain }}` | Public? | Native + SSO | Hardware transcoding via RTX 3060. Public exposure still being reconsidered (VPN-only is the safer call) |
| Sonarr | 8989 | `tv.{{ homelab_domain }}` | Internal | Authentik |
| Radarr | 7878 | `movies.{{ homelab_domain }}` | Internal | Authentik |
| Prowlarr | 9696 | `indexers.{{ homelab_domain }}` | Internal | Authentik |
| qBittorrent | 8080 | `torrent.{{ homelab_domain }}` | Internal | Authentik | Must use VPN/Gluetun |

## Family and Documents (Server 1 - ML350 Gen9)

These services handle critical and precious data, mounting the fast and bulk ZFS pools.

| Service Name | Internal Port | Domain | Exposure | Auth Provider | Notes |
| --- | --- | --- | --- | --- | --- |
| Nextcloud | 8080 | `cloud.{{ homelab_domain }}` | Public | Native + SSO |
| Paperless-ngx | 8000 | `docs.{{ homelab_domain }}` | Public | Authentik |
| Immich | 2283 | `photos.{{ homelab_domain }}` | Public | Native + SSO | Machine learning on RTX 3060 |
| Oikos | 3000 | `family.{{ homelab_domain }}` | Public | Authentik | Family planner |

## AI and Lab (Server 1 - ML350 Gen9)

These services heavily utilize the fast ZFS pool and GPU passthrough.

| Service Name | Internal Port | Domain | Exposure | Auth Provider | Notes |
| --- | --- | --- | --- | --- | --- |
| Ollama | 11434 | `api.{{ homelab_domain }}` | Internal | - | Local LLM backend. Forward-auth breaks API clients anyway, so reach it over VPN |
| LobeHub | 3210 | `chat.{{ homelab_domain }}` | Public | Authentik | Web UI for Ollama |
| Dockge (Main) | 5001 | `compute.{{ homelab_domain }}` | Internal | Authentik | Manages Server 1 stacks |
