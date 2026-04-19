# Home Datacenter

This repository is (will be) the single source of truth for my dual-node home datacenter. It aims to contain the complete Infrastructure as Code configuration, managing everything from hypervisor provisioning and operating system state to the deployment of internal services and reverse proxies.

> Status: Planning phase. Nothing is built yet — hardware is still waiting for an NVMe drive to arrive. Everything in this repo is a working draft. Directions and preferences are noted, but no choice is final. Expect things to change.

## Philosophy & Goals

The guiding principles for this lab, in rough order of priority:

- Reproducibility: everything declared in Git. Manual terminal commands are strictly limited to Day 0 hardware bootstrapping. All ongoing configuration, application deployments, storage management, and state changes are handled declaratively through this repository.
- Maintainability: boring, well-documented tools over clever ones. A tired-me at 2am should be able to understand what past-me built.
- Stability (where it matters): the lab runs real family services (photos, docs, media). For anything in the critical path, uptime and data integrity come before shiny features.
- Room to play: I also like new stuff. Something released yesterday should be testable today — but inside an isolated workspace (Incus testing container, side subdomain, separate dataset), never on top of the critical path. The architecture should make "try the bleeding edge" cheap and "break production" hard.
- Future-proof (within reason): avoid painting myself into corners with exotic stacks or one-vendor lock-in. Pick tools with active communities and clear upgrade paths.
- Easy enough: I'm an engineer, so a reasonable learning curve is fine, but not every piece needs to be a research project. Pragmatism > purity.
- Recoverability: the servers are disposable. Data, secrets, and IaC are not. Any node should be rebuildable from this repo + backups in a single afternoon.

## Architecture Philosophy

The infrastructure is split across two physical nodes to balance always-on availability for critical services with deep compute power for heavy workloads.

- Node 1 (Compute): Acts as the heavy lifter. It handles hardware-accelerated machine learning, media transcoding, most compute/services and massive bulk storage. To keep the baremetal host clean, it utilizes system containers to isolate distinct environments (Production vs. Testing) before running application containers inside them. Powered down at night to save electricity.
- Node 2 (Edge): Acts as the 24/7 sentinel. It is a low-power node dedicated exclusively to critical services (routing, DNS, identity, ...). If the compute node is powered down, the edge node remains online.

## Tech Stack Overview

This is the current thinking, not a final decision. Some slots have a clear preference, others are still wide open. A `?` means actively unsure.

- Infrastructure Automation:
  - Ansible: OS-level configuration (preferred for now)
  - OpenTofu: Declarative management of Incus system containers (preferred for now)

- Virtualization & Containment:
  - Incus: system containers / VMs on the compute node (preferred)
  - Docker: application containers inside Incus workspaces (preferred)

- Storage Subsystem:
  - ZFS: data pools — RAIDZ2 for bulk, mirror for fast (preferred)
  - BTRFS ?: candidate for OS root with snapshot rollback — not decided
  - Base OS also undecided (Debian, NixOS, Fedora, Talos, Flatcar, IncusOS, ...)

- Routing & Security:
  - Caddy ?: ingress / TLS — likely but not locked in
  - caddy-docker-proxy ?: dynamic internal routing — idem
  - Authentik ?: SSO / OIDC — considering alternatives (Pocket-ID, Zitadel, ...)

- Data Protection:
  - Restic ?: backups — strong candidate
  - Rclone ?: cloud sync — strong candidate
  - Cloud target undecided (Backblaze B2, Cloudflare R2, ...)

- Still TBD (no preference yet):
  - Secrets management (see `docs/secrets.md`)
  - Monitoring / alerting
  - Log aggregation
  - Update / image-pin strategy
  - Internal DNS / split-horizon scheme

## Repository Structure

### docs/

Contains docs files

### provision/

Contains OpenTofu files

### configure/

Contains Ansible files

### apps/

Contains apps (Docker compose) files

---

>> Choices are still being made, no choice is definite for now, everything can change. There is still a looot of stuff to think about — taking it slow on purpose. :)
