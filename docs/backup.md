# Backup and Disaster Recovery Strategy

This document outlines the data protection policies, target locations, and automated sync behaviors for the homelab. It follows a modified 3-2-1 strategy optimized for storage costs and data tiers.

## Backup Targets (The Locations)

- Primary Storage (Local 1): ZFS pools (`fast` and `bulk`) on Server 1 (HP ML350 Gen9) and some on Server 2 (AM06 Pro)
- Secondary Storage (Local 2): Dedicated external USB HDD directly attached to Server 1 >> I DO NOT HAVE THIS YET (HOW MUCH ETC IDK)
- Offsite Storage (Cloud): Encrypted object storage bucket. Tool and provider both undecided and deferred until the core lab runs — candidates include Restic/Kopia/Borg/Duplicacy for the tool and Backblaze B2 / Cloudflare R2 / Scaleway / Hetzner / AWS for the target. Choose once Tier 1/2 sizes and monthly cost are known.

## Data Classification & Policies

To manage storage efficiently, data is segmented into three tiers with specific backup rules.

### Tier 1: Critical Data

Definition: Irreplaceable data with a small footprint. If the servers burn down, this is what brings the infrastructure and personal life back online.

- Includes:
  - Docker Compose configurations and environment files
  - Ansible playbooks and IaC repository
  - Password manager databases
  - Critical documents
  - Archives
  - Database dumps
  - Authentik database dump + secrets (edge node) — the edge must stay rebuildable from git + this dump alone
  - an others probably :)
- Policy (Full 3-2-1):
  - Nightly automated backup
  - Encrypted and copied to Local 2 (USB HDD)
  - Encrypted and pushed to Offsite Cloud

### Tier 2: Precious Data

Definition: High-value personal data that is "very" large (hundreds of GB maybe TBs). Losing it would be devastating, but backing it all up to the cloud may be cost-prohibitive

- Includes:
  - Immich photos and home videos
  - Big personal archives
  - Historical data
  - Importants apps data
  - an others probably :)
- Policy (Local Redundancy):
  - Nightly automated backup
  - Encrypted and copied to Local 2 (USB HDD)
  - *Cloud Exception:* Only specific subsets will be pushed Offsite, or full cloud backup will be evaluated based on total size vs. monthly cost

### Tier 3: Replaceable Data

Definition: Massive datasets that can be reacquired from the internet

- Includes:
  - Media library (Movies, TV Shows, ...)
  - Downloaded LLM weights (Ollama)
  - Linux ISOs
  - an others probably :)
- Policy (Zero Backup):
  - Protected solely by the ZFS RAIDZ2 array parity (survives two simultaneous drive failures)
  - Excluded from all local and cloud backup routines to save space and compute overhead

## Backup Window vs. Night Shutdown

Server 1 powers down at night, so "nightly" backups cannot literally run overnight on it.

- Server 1 backup window: in the evening, as the last scheduled job before the nightly shutdown.
- Fallback: if the evening run was missed, the edge node can WoL-wake Server 1, run the backup, then shut it back down.
- Server 2 (edge) is 24/7, so its small Tier 1 backup (configs, Authentik dump) can run overnight as usual.

## Cloud Synchronization (Rclone)

Server 1 acts as the central hub bridging local storage and commercial cloud providers (Google Drive, OneDrive, Proton Drive, ...)

- Sync Strategy: [TODO: Define if Bidirectional or Hub-and-Spoke one-way sync]
- Target Directories: Cloud files will be synced to dedicated datasets......
- Integration: This allows local apps (like Paperless-ngx or Nextcloud) to ingest files dropped into external cloud drives, while maintaining a permanent offline copy of all corporate/personal cloud data, and same for the other way

What needs to be synced :

- Nextcloud to public drives
- Immich to Google Photos / OneDrive
- Documents / archives (paperless?) to soemthing like digiposte

## 4. Recovery Playbook

*This section will document the exact terminal commands to decrypt and restore Tier 1 data from the Offsite Cloud to a fresh machine.*

- [TODO: Write restoration steps once backup software is finalized]
