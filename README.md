# Home Datacenter

This repository is the single source of truth for my dual-node home datacenter. It contains the complete Infrastructure as Code configuration, managing everything from hypervisor provisioning and operating system state to the deployment of internal services and reverse proxies.

The core philosophy of this lab is total reproducibility. Manual terminal commands are strictly limited to Day 0 hardware bootstrapping. All ongoing configuration, application deployments, storage management, and state changes are handled declaratively through this Git repository.

## Architecture Philosophy

The infrastructure is split across two physical nodes to balance high availability for critical services with deep compute power for heavy workloads.

- Node 1 (Compute): Acts as the heavy lifter. It handles hardware-accelerated machine learning, media transcoding, most compute/services and massive bulk storage. To keep the baremetal host clean, it utilizes system containers to isolate distinct environments (Production vs. Testing) before running application containers inside them.
- Node 2 (Edge): Acts as the 24/7 sentinel. It is a low-power node dedicated exclusively to critical servcies (routing, DNS, identity, ...). If the compute node is powered down to save electricity, the edge node remains online.

## Tech Stack Overview

The datacenter relies on a mix of modern infrastructure tools to ensure stability and ease of deployment

- Infrastructure Automation:
  - Ansible: Handles operating system configuration
  - OpenTofu: Communicates with the Incus API to declaratively build and manage system container workspaces

- Virtualization & Containment:
  - Incus
  - Docker

- Storage Subsystem:
  - ZFS: For RAIDZ
  - BTRFS: instant OS-level rollback snapshots

- Routing & Security:
  - Caddy ?
  - caddy-docker-proxy ?
  - Authentik or else

- Data Protection:
  - Restic: Handles backups
  - Rclone: Manages synchronization with cloud providers

## Repository Structure

### docs/

Contains docs files

### provision/

Contains OpenTofu files

### configure/

Contains Ansible files

### apps/

Contains apps (Docker compose) files

>> Choices are still being made, no choice is definite for now, everything can change.
