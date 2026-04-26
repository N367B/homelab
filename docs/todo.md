# TODO / Open Questions

Running list of everything still to decide, design, or build. Ordered roughly from "blocks other decisions" to "nice to have later". Not a strict plan — just a map.

## 0. Foundational decisions — DONE

- [x] Base OS: Debian 13 (Trixie) on both nodes
- [x] Root filesystem: BTRFS subvolumes on mdadm RAID1 (Server 1) / single drive (Server 2), with snapper + grub-btrfs
- [x] Repo visibility: public (treated as already-public during the build)
- [x] Secrets: SOPS + age, master key in Proton Pass + offline paper backup
- [x] IaC stack: Incus + OpenTofu + Ansible + Docker, plus Renovate for dependency PRs
- [x] Ansible runner: interactive runs from admin workstation; scheduled `--check` drift detection from a controller container on the edge node

## 1. Day 0 bootstrap

- [ ] Finish `bootstrap.md` (partitioning details, package selection, preseed/kickstart eventually)
- [ ] Document USB installer creation
- [ ] Settle the admin user name + SSH key workflow
- [ ] First-boot hardening checklist (firewall defaults, SSH config, unattended-upgrades or equivalent)

## 2. Storage

- [ ] Finalize OS boot layout on Server 1 (mirror? single? snapshot tool?)
- [ ] Define ZFS dataset tree for `fast` pool (apps, databases, caches, ...)
- [ ] Define ZFS dataset tree for `bulk` pool (media, immich, nextcloud, archives, ...)
- [ ] Pick recordsize / compression / atime per dataset
- [ ] UID/GID scheme across host + Incus + Docker (avoid permission hell)
- [ ] Source a USB HDD for Local 2 backups (size? budget?)
- [ ] Decide ZFS native snapshots tool (Sanoid/Syncoid? zfs-autosnapshot? custom?)

## 3. Network

- [ ] Lock in final subnet plan (fix the `10.10.1.0` duplicate for LXC/VMs)
- [ ] Configure VLANs on the XikeStor switch (Core / Homelab / IoT / Mgmt)
- [ ] Decide how to block Livebox IPv6 RAs (switch-level filter? bridge config?)
- [ ] Run own IPv6 RA from edge node with custom DNS
- [ ] Wake-on-LAN: BIOS + OS + edge-side trigger (magic packet from AdGuard/edge)
- [x] Internal DNS / split-horizon: public DNS resolves home public IP, AdGuard resolves `*.{{ homelab_domain }}` to edge internally
- [ ] Remote access: WireGuard? Tailscale? Both?
- [ ] Firewall scheme (host-level nftables? edge gateway? per-VLAN rules?)

## 4. Identity, routing, TLS

- [x] Reverse proxy: Caddy on edge
- [x] Routing config source: Caddyfile in Git
- [x] Identity provider: Authentik
- [x] TLS strategy: Let's Encrypt DNS-01 via Cloudflare; per-host certs by default, wildcard optional
- [ ] Which services are exposed to the internet vs LAN/VPN only (Jellyfin: reconsider public exposure)
- [ ] OIDC integration plan per app (native + SSO vs proxy auth)

## 5. Secrets management

- [ ] Pick the tool (see 0.)
- [ ] Define the workflow for adding a new secret
- [ ] Define rotation policy
- [ ] Where does the master/recovery key live? (password manager + offline paper backup?)
- [ ] Bootstrap chicken-and-egg: how does a fresh machine get its first key?

## 6. Observability (currently nothing planned)

- [ ] Pick a metrics stack (Prometheus+Grafana? Beszel? Netdata?)
- [ ] Pick a log stack (Loki? journald only? Vector?)
- [ ] Alerting target (ntfy? email? Telegram? Gotify?)
- [ ] Minimum alerts for day 1: disk SMART, ZFS scrub/errors, UPS battery, host down, service down, cert expiry, backup failure
- [ ] Uptime check (external ping of the edge) — Uptime Kuma? Healthchecks.io?

## 7. Backup & recovery

- [ ] Pick offsite cloud provider (Backblaze B2 / Cloudflare R2 / ...) and estimate monthly cost
- [ ] Lock in Restic (or alternative: Kopia, Borg, ...)
- [ ] Rclone sync strategy per source (one-way vs bidi)
- [ ] Write `recovery.md` with literal restore steps from cold cloud
- [ ] Schedule a yearly restore drill
- [ ] Decide Immich / Nextcloud specific backup (DB dump + data vs app-aware export)
- [ ] Decide what from Server 2 gets backed up (configs at minimum)

## 8. Operations

- [x] Update strategy: Renovate (Docker image tags in compose, OpenTofu providers, Ansible collections, GitHub Actions)
- [ ] No Watchtower — confirm alternative cadence
- [ ] UPS integration: NUT on edge, graceful shutdown script for compute (<30% battery)
- [ ] Night shutdown / wake schedule for Server 1 (cron? scripted? manual?)
- [ ] CI for this repo? (linting ansible/opentofu, ansible --check on PRs, ...)
- [ ] Tagged releases / rollback strategy for IaC

## 9. Edge SPOF mitigation

- [ ] Secondary DNS resolver on Server 1 (so DNS survives if edge dies during the day)
- [ ] Can the lab be rebuilt on a spare mini-PC in < 1 hour? Test it.
- [ ] Document the manual recovery path if the edge is dead

## 10. Polish / smaller items

- [ ] Gluetun kill-switch health check for qBittorrent
- [ ] iLO firmware fan control issue (workaround or accept)
- [ ] Fill in `services.md` as services come online (ports, auth, notes)
- [ ] Fill in all the `TODO` placeholders scattered across `docs/`
- [ ] Diagram: network topology (one clear PNG/SVG)
- [ ] Diagram: service dependency graph

## 11. Stretch / future

- [ ] Second edge node for true HA (cheap mini-PC?)
- [ ] Off-site mirror (friend's place? parents' house?)
- [ ] Hardware security key (Yubikey) as root-of-trust for secrets
- [ ] Bare-metal monitoring of the UPS via SNMP NIC (requires buying the card)
- [ ] Consider k3s / k8s for the "testing" workspace (learning, not production)
