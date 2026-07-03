# Backup and Disaster Recovery Strategy

This document outlines the data protection policies, target locations, and automated sync behaviors for the homelab. It follows a modified 3-2-1 strategy optimized for storage costs and data tiers.

## Backup Targets (The Locations)

- Primary Storage (Local 1): ZFS pools (`fast` and `bulk`) on Server 1 (HP ML350 Gen9) and some on Server 2 (AM06 Pro)
- Secondary Storage (Local 2): Dedicated external USB HDD directly attached to Server 1 >> I DO NOT HAVE THIS YET (HOW MUCH ETC IDK)
- Offsite Storage (Cloud): encrypted object storage bucket. Tool choice is Restic for now; provider is still undecided. Candidates include Backblaze B2, Cloudflare R2, Scaleway, Hetzner, and AWS. Choose once Tier 1/2 sizes and monthly cost are known.

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

## Backup Tooling Model

Restic is the current backup engine. The goal is to keep backup definitions declarative and service-oriented instead of building custom archive scripts.

For each service, define:

- File paths to back up, such as config directories, uploaded data, and small persistent volumes.
- Logical database dump jobs, such as `pg_dump`, backed up through Restic stdin.
- Backup tier for each path: Tier 1, Tier 2, or Tier 3.
- Restore notes once the service becomes important.

Rules of thumb:

- Git + SOPS is the source of truth for deployable configuration and secrets.
- Restic backs up runtime state that cannot be recreated from Git.
- Databases should have logical dumps. Raw database volumes are not the primary restore path.
- ZFS/BTRFS snapshots are fast rollback, not disaster recovery.
- Tier 1 goes local and offsite.
- Tier 2 goes local, and offsite either fully or by selected subset depending on size/cost.
- Tier 3 is excluded from Restic/offsite unless there is a specific reason.

## Edge Backup: Current Implementation

Status: first local Restic repository implemented for Server 2 (`edge`). This is the first recovery layer, not the final offsite strategy.

The edge node backs up to a local Restic repository:

- Repository: `/var/backups/restic/edge`
- Password: SOPS secret `secrets/edge-backup.sops.yaml`
- Timer: `homelab-edge-restic.timer`
- Schedule: daily around 03:30 with a randomized delay
- Retention: 14 daily, 8 weekly, 12 monthly snapshots, with prune

Included edge state:

- `/opt/stacks` — deployed compose files, rendered env files, and bind-mounted app config such as Home Assistant
- Caddy Docker volumes — ACME account/certificate state
- AdGuard work volume
- Authentik logical PostgreSQL dump, stored in Restic as `authentik.dump`

The edge backup role is intentionally declarative. Add new file backup sets or database dump jobs in `configure/group_vars/edge_nodes.yml`:

```yaml
edge_restic_file_sets:
  - name: edge-files
    tags: [edge, files]
    paths:
      - /opt/stacks

edge_restic_stdin_jobs:
  - name: authentik-db
    tags: [edge, authentik-db]
    filename: authentik.dump
    command: docker exec authentik-postgresql-1 pg_dump --username authentik --dbname authentik --format custom
```

Useful commands on `edge`:

```sh
sudo systemctl start homelab-edge-restic.service
sudo systemctl status homelab-edge-restic.service
sudo restic -r /var/backups/restic/edge --password-file /root/.config/restic/edge-password snapshots
sudo restic -r /var/backups/restic/edge --password-file /root/.config/restic/edge-password ls latest
```

This local repository protects against bad deploys, accidental deletion, and simple rollback needs. It does not protect against edge disk loss or fire/theft. The next step is to add a second Restic repository or copy target on USB/offsite storage using the same backup sets.

## Offsite Backup Direction

The first offsite target should cover Tier 1 only. Edge state is small, so it is the easiest and cheapest place to start.

Recommended first phase:

- Keep the current local Restic repo on `edge`.
- Add a second Restic repository on OVH Object Storage Standard for Tier 1 edge state.
- Use the same file sets and stdin database jobs.
- Keep separate credentials from Caddy/DDNS Cloudflare tokens.
- Store repository credentials in SOPS.

The Ansible role already has an offsite switch. Once the OVH bucket and S3 credentials exist, set these variables for `edge`:

```yaml
edge_restic_offsite_enabled: true
edge_restic_offsite_repo: s3:https://s3.<region>.io.cloud.ovh.net/<bucket-name>
edge_restic_offsite_password_file: /root/.config/restic/edge-ovh-password
edge_restic_offsite_env_file: /root/.config/restic/edge-ovh.env
```

And add these SOPS values to `secrets/edge-backup.sops.yaml`:

```yaml
edge_restic_offsite_password: <different restic repo password>
edge_restic_offsite_access_key: <OVH S3 access key>
edge_restic_offsite_secret_key: <OVH S3 secret key>
```

Provider tradeoffs:

Provider | Fit | Notes
--- | --- | ---
Backblaze B2 | Strong default | Mature S3-compatible object storage, predictable enough, commonly used with Restic
Cloudflare R2 | Good if already using Cloudflare | No egress fees, but pricing/semantics should be checked against Restic usage
Scaleway Object Storage | Good EU option | Region close to home, S3-compatible
Hetzner Storage Box | Good cheap non-object option | Works well over SFTP/Restic REST/Rclone patterns, less cloud-native than S3
AWS S3 | Most mature | Usually not the cheapest or simplest for a homelab

Current recommendation: start with Backblaze B2 or Scaleway for the first offsite Restic repository unless Cloudflare R2 pricing/behavior looks clearly better at the expected size.

Do not put Tier 3 data in cloud backup. Decide Tier 2 offsite coverage only after real sizes are known.

## Service Backup Checklist

When adding a service, update its backup design before treating it as production:

- Classify each data path as Tier 1, Tier 2, or Tier 3.
- Add config and small runtime state to a Restic file set.
- Add a logical dump job for each database.
- Exclude caches, thumbnails, generated media, and replaceable downloads unless intentionally kept.
- Add restore notes for the service once the backup has been tested.

Examples:

Service | Database | Files | Tier notes
--- | --- | --- | ---
Authentik | `pg_dump` | `/opt/stacks/authentik`, Caddy/Auth data | Tier 1
Home Assistant | Usually SQLite/config backup initially | `/opt/stacks/homeassistant/config` | Tier 1 if automations matter
AdGuard Home | Config/work state | AdGuard config/work | Tier 1 for DNS/DHCP recovery
Immich | Postgres dump | photos/videos library | DB is Tier 1, photos/videos are Tier 2
Nextcloud | DB dump | user files/config | DB/config Tier 1, user files Tier 2
Paperless-ngx | DB dump | documents/media/export | Tier 1 or Tier 2 depending on document set
Jellyfin | Optional | config only | media is Tier 3

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
