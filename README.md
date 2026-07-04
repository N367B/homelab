# Home Datacenter

This repo tracks my dual-node home datacenter. It covers operating system state, edge services, application stacks, secrets, and the notes I need to rebuild or operate the lab.

> Status: actively building. The edge node and core services come first. The compute node and the larger app stack are still catching up, so some docs describe the intended design rather than deployed state.

## Philosophy & Goals

The guiding principles for this lab, in rough order of priority:

- Reproducibility: everything important lives in Git. Manual terminal commands are limited to Day 0 hardware bootstrapping. Ongoing configuration, application deployments, storage management, and state changes should come from this repo.
- Maintainability: boring, well-documented tools over clever ones. A tired-me at 2am should be able to understand what past-me built.
- Stability (where it matters): the lab runs real family services (photos, docs, media). For anything in the critical path, uptime and data integrity come before shiny features.
- Room to experiment: new tools should be easy to test in isolated workspaces, never directly on the critical path. Trying the bleeding edge should be cheap. Breaking production should be hard.
- Future-proof (within reason): avoid painting myself into corners with exotic stacks or one-vendor lock-in. Pick tools with active communities and clear upgrade paths.
- Easy enough: I'm an engineer, so a reasonable learning curve is fine, but not every piece needs to be a research project. Pragmatism > purity.
- Recoverability: the servers are disposable. Data, secrets, and IaC are not. Any node should be rebuildable from this repo + backups in a single afternoon.

## Architecture Philosophy

The lab is split across two physical nodes, with one small always-on machine and one larger compute/storage box.

- Node 1 (Compute): heavy workloads, hardware-accelerated machine learning, media transcoding, most application services, and bulk storage. The plan is to keep the bare-metal host clean with Incus workspaces before running application containers inside them. Powered down at night to save electricity.
- Node 2 (Edge): always-on critical services such as ingress, DNS, identity, VPN, and backup automation. If the compute node is powered down, the edge node remains online.

## Tech Stack Overview

Current stack, with some compute-node pieces still planned rather than implemented.

- Infrastructure Automation:
  - Ansible: OS-level configuration. Interactive runs from the admin workstation. Scheduled `--check` drift detection will run from a small controller container on the edge node
  - OpenTofu: Incus system containers on the compute node
  - Renovate: automated dependency PRs (Docker image tags in compose, OpenTofu providers, Ansible collections, GitHub Actions)

- Virtualization & Containment:
  - Incus: system containers / VMs on the compute node
  - Docker: application containers inside Incus workspaces

- Storage Subsystem:
  - ZFS: data pools, with RAIDZ2 for bulk and a mirror for fast storage
  - BTRFS: OS root with subvolumes + snapper for host snapshots. grub-btrfs boot entries are planned once the upstream install task exists (native BTRFS RAID1 on Server 1 for checksum self-healing)
  - Base OS: Debian 13 (Trixie) on both nodes

- Secrets Management:
  - SOPS + age: file-based, encrypted at rest in git, decrypted at deploy time. Master age key in Proton Pass + offline paper backup.

- Routing & Security:
  - Caddy: edge reverse proxy / TLS termination
  - Authentik: identity provider, OIDC, and forward-auth for services that need proxy-side auth

- Remote Access:
  - WireGuard on the edge node (PulseHeberg VPS as rendezvous fallback)

- In progress / still open:
  - Compute-node provisioning and application stacks
  - Monitoring, alerting, and log aggregation
  - Full offsite backup coverage beyond the initial Restic edge backup

## Repository Structure

### docs/

Architecture, decisions, runbooks, and open questions

### provision/

OpenTofu for planned Incus containers and VMs on the compute node

### configure/

Ansible OS baseline and per-node roles. `site.yml` is the entry point

### apps/

Docker Compose stacks, one directory per stack, grouped by node

### secrets/

SOPS-encrypted secrets with age. See `.sops.yaml` at the repo root

The repo is incremental on purpose. Edge services are implemented first, while compute-node services and deeper runbooks are added as they become real.
