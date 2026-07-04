# Storage Topology & Management

## Server 1 (Compute - HP ML350 Gen9)

### OS Boot Drive (BTRFS native RAID1)

- Drives: 2 x 240GB Samsung PM863A SATA SSDs
- Layout: identical partitions on both drives
  - `sdX1` 1 GiB ESP (FAT32). Not mirrored. GRUB installed to both ESPs so either disk can boot solo
  - `sdX2` rest BTRFS. Both partitions are members of one BTRFS filesystem with `raid1` data + metadata profiles
- Why native RAID1 instead of mdadm: BTRFS checksums every block. With native RAID1 it knows about both copies, so a failed checksum is healed automatically from the good disk and `btrfs scrub` repairs proactively. On top of mdadm it could only detect corruption, not repair it. Also one less layer to manage.
- Known tradeoff: if a disk dies completely, boot requires adding `rootflags=degraded` once at the GRUB prompt via iLO console. Accepted and documented in `bootstrap.md`.
- Two-device RAID1 degraded handling is a known sharp edge: while degraded, new writes can land as `single`-profile chunks, and the array should be returned to full RAID1 promptly rather than left running degraded across reboots. Recovery path: boot `degraded`, `btrfs replace` the dead disk, then confirm `btrfs filesystem usage /` shows no `single` chunks. Avoid repeated degraded reboots.
- Install path: the Debian installer sets up BTRFS on `sda2` only. The second device is added and converted to RAID1 on first boot with `btrfs device add` + `btrfs balance -dconvert=raid1 -mconvert=raid1`. The conversion must leave Data, Metadata, and System all at RAID1 with zero `single` chunks remaining. `bootstrap.md` verifies this with `btrfs filesystem usage /`.
- File System: BTRFS with subvolumes
  - `@` → `/`
  - `@home` → `/home`
  - `@var` → `/var`
  - `@log` → `/var/log` (excluded from snapshots)
  - `@snapshots` → `/.snapshots`
- Snapshots: `snapper` with apt pre/post hooks. `grub-btrfs` boot menu integration is planned after an upstream install task is added.
- Scrub: monthly `btrfs scrub` through a systemd timer managed by Ansible. This is what actually triggers self-healing
- Swap: zram (compressed RAM swap), no on-disk swap
- Purpose: Host OS Debian 13, Incus binaries

### Pool 1: "fast" (ZFS Mirror)

- Drives: 2 x 1TB NVMe (WD BLACK SN750 + Samsung PM9A1a)
- Topology: ZFS Mirror (`zpool create fast mirror /dev/nvme0n1 /dev/nvme1n1`)
- Datasets: to be defined when compute workloads move onto the node

### Pool 2: "bulk" (ZFS RAIDZ2)

- Drives: 6 x 10TB HGST/WD Ultrastar SAS
- Topology: ZFS RAIDZ2 (`zpool create bulk raidz2 drive1 drive2... drive6`)
- Usable Space: ~40TB
- Datasets: to be defined from the final media, archive, and backup layout

---

## Server 2 (Edge - AM06 Pro)

### OS & App Drive

- Drive: 1 x 512GB Samsung PM9A1 NVMe
- Layout:
  - `nvme0n1p1` 1 GiB ESP (FAT32)
  - `nvme0n1p2` rest BTRFS, same subvolume layout as Server 1 (no RAID, single drive)
- Snapshots: `snapper`. Planned `grub-btrfs` boot menu integration once implemented, same model as Server 1
- Swap: zram
- Mount Point: `/`
- Purpose: Host OS Debian 13, baremetal Docker containers (Caddy, Authentik, AdGuard, ...)

---

## File Permissions Strategy (UID/GID)

Container UID/GID allocation is still being standardized. Service-owned data should stay predictable across Docker, Incus, and backup restores.
