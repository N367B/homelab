# TODO / Open Questions

Running list of everything still to decide, design, or build. Ordered roughly from "blocks other decisions" to "nice to have later". Not a strict plan — just a map.

## 0. Foundational decisions — DONE

- [x] Base OS: Debian 13 (Trixie) on both nodes
- [x] Root filesystem: BTRFS subvolumes on native BTRFS RAID1 (Server 1) / single drive (Server 2), with snapper
- [ ] Add upstream `grub-btrfs` install task before treating boot-menu rollback as implemented
- [x] Repo visibility: public (treated as already-public during the build)
- [x] Secrets: SOPS + age, master key in Proton Pass + offline paper backup
- [x] IaC stack: Incus + OpenTofu + Ansible + Docker, plus Renovate for dependency PRs
- [x] Ansible runner: interactive runs from admin workstation; scheduled `--check` drift detection from a controller container on the edge node

## 1. Day 0 bootstrap

- [ ] Finish `bootstrap.md` (preseed/kickstart eventually)
- [ ] Document USB installer creation
- [x] Admin user: `noe` on both nodes, key-only SSH, passwordless sudo; hostnames `compute` / `edge` (see `bootstrap.md`)
- [ ] First-boot hardening checklist (firewall defaults, SSH config, unattended-upgrades or equivalent)

## 2. Storage

- [x] OS boot layout on Server 1: BTRFS native RAID1 over both SSDs (install on one, convert on first boot) — see `storage.md` / `bootstrap.md`
- [ ] Define ZFS dataset tree for `fast` pool (apps, databases, caches, ...)
- [ ] Define ZFS dataset tree for `bulk` pool (media, immich, nextcloud, archives, ...)
- [ ] Pick recordsize / compression / atime per dataset
- [ ] UID/GID scheme across host + Incus + Docker (avoid permission hell)
- [ ] Prototype early: one Incus container + one Docker compose app + one bind-mounted ZFS dataset on a throwaway pool, to validate the idmap/UID story before designing the full dataset tree
- [ ] Source a USB HDD for Local 2 backups (size? budget?)
- [ ] Decide ZFS native snapshots tool (Sanoid/Syncoid? zfs-autosnapshot? custom?)

## 3. Network

- [x] Lock in final subnet plan (the `10.10.1.0` duplicate is fixed in `network.md`: incus `10.10.20.0/24`, vms `10.10.30.0/24`, apps `10.10.40.0/24`)
- [ ] Configure VLANs on the XikeStor switch (Core / Homelab / IoT / Mgmt)
- [ ] Decide how to block Livebox IPv6 RAs (switch-level filter? bridge config?)
- [ ] Run own IPv6 RA from edge node with custom DNS
- [ ] Wake-on-LAN: BIOS + OS + edge-side trigger (magic packet from AdGuard/edge)
- [ ] Ansible-manage the static interface config (set manually at Day 0 per `bootstrap.md`; move `/etc/network/interfaces.d/static` into the baseline role for reproducibility, carefully — rewriting it can drop the SSH connection)
- [x] Internal DNS / split-horizon: public DNS resolves home public IP, AdGuard resolves `*.{{ homelab_domain }}` to edge internally
- [x] Remote access: plain WireGuard on the edge node (no third-party dependency; Tailscale can be added later if it gets annoying)
- [ ] Firewall scheme (host-level nftables? edge gateway? per-VLAN rules?)

## 4. Identity, routing, TLS

- [x] Reverse proxy: Caddy on edge
- [x] Routing config source: Caddyfile in Git
- [x] Identity provider: Authentik
- [x] TLS strategy: Let's Encrypt DNS-01 via Cloudflare; per-host certs by default, wildcard optional
- [x] Default exposure policy: family-facing apps public, admin/infra tools (AdGuard, Dockge, *arr, qBittorrent, Ollama API) internal-only — see `services.md` exposure table
- [ ] Jellyfin: decide public vs VPN-only (still reconsidering)
- [ ] OIDC integration plan per app (native + SSO vs proxy auth)

## 5. Secrets management

- [x] Pick the tool: SOPS + age (see 0.)
- [ ] Define the workflow for adding a new secret
- [ ] Define rotation policy
- [x] Master/recovery key: Proton Pass + offline paper backup (see 0.)
- [x] Bootstrap chicken-and-egg: `scp` the age key from the admin workstation during Day 0 (documented in `bootstrap.md` step 4)

## 6. Observability (currently nothing planned)

- [ ] Pick a metrics stack (Prometheus+Grafana? Beszel? Netdata?)
- [ ] Pick a log stack (Loki? journald only? Vector?)
- [ ] Alerting target (ntfy? email? Telegram? Gotify?)
- [ ] Minimum alerts for day 1: disk SMART, ZFS scrub/errors, UPS battery, host down, service down, cert expiry, backup failure
  - Likely cheapest path: smartd + ZED mail/ntfy hooks first, Prometheus/Grafana as a later phase once services exist
- [ ] Uptime check (external ping of the edge) — run Uptime Kuma (or similar) on the PulseHeberg VPS so monitoring survives a home outage

## 7. Backup & recovery

Restic is now the selected backup engine for the first implementation. Local edge backups are live; offsite target and compute backup details are still open.

- [x] Backup tool: Restic for the first implementation
- [ ] Offsite target: undecided (Backblaze B2, Cloudflare R2, Scaleway, Hetzner, AWS, ... — pick once Tier 1/2 sizes and monthly cost are known)
- [ ] Rclone sync strategy per source (one-way vs bidi)
- [ ] Write `recovery.md` with literal restore steps from cold cloud
- [ ] Schedule a yearly restore drill
- [ ] Decide Immich / Nextcloud specific backup (DB dump + data vs app-aware export)
- [x] Decide what from Server 2 gets backed up initially: `/opt/stacks`, Caddy state, AdGuard work, Authentik DB dump

## 8. Operations

- [x] Update strategy: Renovate (Docker image tags in compose, OpenTofu providers, Ansible collections, GitHub Actions)
- [ ] No Watchtower — confirm alternative cadence
- [ ] UPS integration: NUT on edge, graceful shutdown script for compute (<30% battery)
- [ ] Night shutdown / wake schedule for Server 1 (cron? scripted? manual?)
- [ ] CI for this repo? (linting ansible/opentofu, ansible --check on PRs, ...)
- [ ] Tagged releases / rollback strategy for IaC

## 9. Edge SPOF mitigation

- [ ] Secondary DNS resolver on Server 1 (so DNS survives if edge dies during the day)
- [ ] Keep edge state minimal by design: compose files + SOPS in git, Authentik DB dump backed up off-box nightly (see `backup.md`) — target: fresh Debian + `bootstrap.md` + one Ansible run + one DB restore < 1 hour
- [ ] Can the lab be rebuilt on a spare mini-PC in < 1 hour? Test it.
- [ ] Document the manual recovery path if the edge is dead
- [ ] VPS as WireGuard rendezvous fallback (reach home even if the public IP changed while away) + secondary DNS candidate

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
