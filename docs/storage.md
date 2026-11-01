# Storage Topology & Management

## Server 1 (Compute - HP ML350 Gen9)

### OS Boot Drive (BTRFS native RAID1)

- Drives: 2 x 240GB Samsung PM863A SATA SSDs
- Layout: identical partitions on both drives
  - `p1` 1 GiB ESP (FAT32). Not mirrored. GRUB is copied to the second ESP at install, with its own firmware boot entry, so either disk can boot solo (see `bootstrap.md`)
  - `p2` rest BTRFS. Both partitions are members of one BTRFS filesystem with `raid1` data + metadata profiles
- Why native RAID1 instead of mdadm: BTRFS checksums every block. With native RAID1 it knows about both copies, so a failed checksum is healed automatically from the good disk and `btrfs scrub` repairs proactively. On top of mdadm it could only detect corruption, not repair it. Also one less layer to manage.
- Known tradeoff: if a disk dies completely, boot requires adding `rootflags=degraded` once at the GRUB prompt via iLO console. Accepted and documented in `bootstrap.md`.
- Two-device RAID1 degraded handling is a known sharp edge: while degraded, new writes can land as `single`-profile chunks, and the array should be returned to full RAID1 promptly rather than left running degraded across reboots. Recovery path: boot `degraded`, `btrfs replace` the dead disk, then confirm `btrfs filesystem usage /` shows no `single` chunks. Avoid repeated degraded reboots.
- Install path: the Debian installer sets up BTRFS on the first SSD only. The second device is added and converted to RAID1 on first boot with `btrfs device add` + `btrfs balance -dconvert=raid1 -mconvert=raid1`. The conversion must leave Data, Metadata, and System all at RAID1 with zero `single` chunks remaining. `bootstrap.md` verifies this with `btrfs filesystem usage /`.
- Subvolumes: root stays on the `@rootfs` subvolume made by the installer. Snapper adds `/.snapshots` below it. The host holds no data of its own (pools are on ZFS, config is in git), so there is no separate `@home`, `@var` or `@log`.
- Snapshots: `snapper` config `root` with the Debian apt hook, so every apt run gets a pre and post snapshot. No timeline snapshots. Up to 20 numbered snapshots are kept. There is no grub-btrfs boot menu. Rolling back means booting a snapshot from the GRUB prompt or restoring files from `/.snapshots`.
- Scrub: monthly `btrfs scrub` through a systemd timer managed by Ansible. This is what actually triggers self-healing
- Swap: zram (compressed RAM swap), no on-disk swap
- Purpose: Host OS Debian 13, Incus binaries
- Updates: unattended-upgrades installs everything on this node, kernel, ZFS, the NVIDIA driver and Incus from Zabbly included, with a snapper snapshot before and after each run. The node is off every night, so a new kernel is in use from the next morning. A kernel update rebuilds the ZFS and NVIDIA modules with DKMS. If a build fails, `homelab-boot-check` alerts 3 minutes after boot on missing pools or a missing GPU, and the previous kernel stays under Advanced options in GRUB.

### ZFS on the compute node

The role `zfs` installs OpenZFS from Debian contrib (DKMS), creates missing pools and datasets, caps the ARC at 64 GiB (OpenZFS 2.3 otherwise lets it grow to nearly all of the 256 GB), enables a monthly scrub per pool and a monthly TRIM on SSD pools, and configures ZED. Pool definitions live in `configure/group_vars/compute_nodes.yml`.

- Pools are created only when absent, and never with `-f`. The role stops when a pool with the same name can be imported from the disks. `zpool create` itself refuses disks that belong to another pool. Old pools are destroyed by hand (see `bootstrap.md`).
- Disks are named by `/dev/disk/by-id`, because the `sdX` letters change between boots on this machine.
- Common properties: `ashift=12`, `atime=off`, `xattr=sa`, `acltype=posix` (POSIX ACLs, which ZFS also accepts as `posixacl`), `dnodesize=auto`. `ashift` is fixed at creation. The NVMe drives report 512-byte sectors, so without it ZFS picks 9.
- Scrubs: the packaged `zfs-scrub-monthly@<pool>.timer` is persistent, so a scrub missed while compute was off starts at the next boot. Its service pauses the scrub on shutdown and the next run resumes it. The `fast` pool also gets `zfs-trim-monthly@fast.timer`, because `autotrim` skips small frees. The Debian cron that scrubs and trims at 00:24 on Sundays is turned off per pool (`org.debian:periodic-scrub` and `org.debian:periodic-trim` set to `disable`), since compute is off at that hour and the timers already cover it.

### Pool 1: "fast" (ZFS Mirror)

- Drives: 2 x 1TB NVMe (WD BLACK SN750 + Samsung PM9A1a)
- Topology: ZFS mirror, created by the `zfs` role. Extra properties `compression=lz4` and `autotrim=on`
- Datasets: `fast/incus` is the Incus storage pool, created by Incus itself. The rest is to be defined when compute workloads move onto the node

### Pool 2: "bulk" (ZFS RAIDZ2)

- Drives: 6 x 10TB HGST/WD Ultrastar SAS
- Topology: ZFS RAIDZ2, created by the `zfs` role. Extra property `compression=zstd`
- Usable Space: ~36TB after RAIDZ2 parity and ZFS overhead (measured on the October 2026 test pool)
- Datasets: `bulk/media` (`recordsize=1M`). The rest is to be defined from the final media, archive, and backup layout

---

## Server 2 (Edge - AM06 Pro)

### OS & App Drive

- Drive: 1 x 512GB Samsung PM9A1 NVMe
- Layout:
  - `nvme0n1p1` 1 GiB ESP (FAT32)
  - `nvme0n1p2` rest BTRFS, root on the installer's `@rootfs` subvolume (no RAID, single drive)
- Snapshots: `snapper` is installed but has no config yet. Enabling `snapper_root` gives the same apt snapshots as Server 1
- Swap: zram
- Mount Point: `/`
- Purpose: Host OS Debian 13, baremetal Docker containers (Caddy, Authentik, AdGuard, ...)

---

## File Permissions Strategy (UID/GID)

Container UID/GID allocation is still being standardized. Service-owned data should stay predictable across Docker, Incus, and backup restores.
