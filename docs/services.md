# Homelab Services and Routing Directory

This document serves as the master cheat sheet for internal ports, external domains, and authentication policies. All ports, domains, and auth policies are subject to change during the build process.

>> MAny Services will be addes later, only the miain ones are here for now.

## Edge and Core Infrastructure (Server 2 - AM06 Pro)

These services run 24/7 on the edge node and handle network ingress, identity, and DNS.

Service Name | Internal Port | External Domain | Auth Provider | Notes
--- | --- | --- | --- | ---
Caddy | 80, 443 | - | - | Master ingress proxy
Authentik | 9000 | auth.{{ homelab_domain }} | Public | SSO Provider
AdGuard Home | 3000 | dns.{{ homelab_domain }} | Authentik | Internal DNS and DHCP
Dockge (Edge) | 5001 | edge.{{ homelab_domain }} | Authentik | Manages Server 2 stacks

## Media Stack (Server 1 - ML350 Gen9)

These services run on the main compute node and mount the bulk ZFS pool.

Service Name | Internal Port | External Domain | Auth Provider | Notes
--- | --- | --- | --- | ---
caddy-docker-proxy | 80 | - | - | Dynamic internal router
Jellyfin | 8096 | media.{{ homelab_domain }} | Native + SSO | Hardware transcoding via RTX 3060
Sonarr | 8989 | tv.{{ homelab_domain }} | Authentik | 
Radarr | 7878 | movies.{{ homelab_domain }} | Authentik | 
Prowlarr | 9696 | indexers.{{ homelab_domain }} | Authentik | 
qBittorrent | 8080 | torrent.{{ homelab_domain }} | Authentik | Must use VPN/Gluetun

## Family and Documents (Server 1 - ML350 Gen9)

These services handle critical and precious data, mounting the fast and bulk ZFS pools.

Service Name | Internal Port | External Domain | Auth Provider | Notes
--- | --- | --- | --- | ---
Nextcloud | 8080 | cloud.{{ homelab_domain }} | Native + SSO | 
Paperless-ngx | 8000 | docs.{{ homelab_domain }} | Authentik | 
Immich | 2283 | photos.{{ homelab_domain }} | Native + SSO | Machine learning on RTX 3060
Oikos | 3000 | family.{{ homelab_domain }} | Authentik | Family planner

## AI and Lab (Server 1 - ML350 Gen9)

These services heavily utilize the fast ZFS pool and GPU passthrough.

Service Name | Internal Port | External Domain | Auth Provider | Notes
--- | --- | --- | --- | ---
Ollama | 11434 | api.{{ homelab_domain }} | Authentik | Local LLM backend
LobeHub | 3210 | chat.{{ homelab_domain }} | Authentik | Web UI for Ollama
Dockge (Main) | 5001 | compute.{{ homelab_domain }} | Authentik | Manages Server 1 stacks
