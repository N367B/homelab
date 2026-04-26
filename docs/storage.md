# Storage Topology & Management

## Server 1 (Compute - HP ML350 Gen9)

### OS Boot Drive (mdadm RAID1 + BTRFS)

- Drives: 2 x 240GB Samsung PM863A SATA SSDs
- Layout: identical partitions on both drives
  - `sdX1`  1 GiB  ESP (FAT32) — not mirrored, GRUB installed to both ESPs so either disk can boot solo
  - `sdX2`  rest    Linux RAID member → assembled as `/dev/md0` (mdadm RAID1, metadata 1.2)
- File System: BTRFS on `/dev/md0` with subvolumes
  - `@`          → `/`
  - `@home`      → `/home`
  - `@var`       → `/var`
  - `@log`       → `/var/log` (excluded from snapshots)
  - `@snapshots` → `/.snapshots`
- Snapshots: `snapper` with apt pre/post hooks; `grub-btrfs` exposes snapshots in the boot menu so a bad upgrade can be rolled back in one reboot
- Swap: zram (compressed RAM swap) — no on-disk swap
- Purpose: Host OS Debian 13, Incus binaries

### Pool 1: "fast" (ZFS Mirror)

- Drives: 2 x 1TB NVMe (WD BLACK SN750 + Samsung PM9A1a)
- Topology: ZFS Mirror (`zpool create fast mirror /dev/nvme0n1 /dev/nvme1n1`)
- Datasets:
  - TODO

### Pool 2: "bulk" (ZFS RAIDZ2)

- Drives: 6 x 10TB HGST/WD Ultrastar SAS
- Topology: ZFS RAIDZ2 (`zpool create bulk raidz2 drive1 drive2... drive6`)
- Usable Space: ~40TB
- Datasets:
  - TODO

---

## Server 2 (Edge - AM06 Pro)

### OS & App Drive

- Drive: 1 x 512GB Samsung PM9A1 NVMe
- Layout:
  - `nvme0n1p1`  1 GiB   ESP (FAT32)
  - `nvme0n1p2`  rest    BTRFS, same subvolume layout as Server 1 (no RAID, single drive)
- Snapshots: `snapper` + `grub-btrfs` (same model as Server 1)
- Swap: zram
- Mount Point: `/`
- Purpose: Host OS Debian 13, baremetal Docker containers (Caddy, Authentik, AdGuard, ...)

---

## File Permissions Strategy (UID/GID)

TODO
