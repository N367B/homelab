# Storage Topology & Management

## Server 1 (Compute - HP ML350 Gen9)

### OS Boot Drive (mdadm RAID1 Mirror)

- Drives: 2 x 240GB Samsung PM863A SATA SSDs
- File System: ext4 or BTRFS --- CAN BE CHANGED (ZFS ? LVM ? XFS ?)
- Mount Point: `/`
- Purpose: Host OS Debian, Incus binaries --- CAN BE CHANGED (Proxmox, NixOS, Fedora, Talos, Flatcar Container, IncusOS, ...)

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

- Drive: 1 x 512GB SSD
- File System: BTRFS --- CAN BE CHANGED (ZFS ? LVM ? XFS ?)
- Mount Point: `/`
- Purpose: Host OS Debian, baremetal Docker containers --- CAN BE CHANGED (Proxmox, NixOS, Fedora, Talos, Flatcar Container, IncusOS, ...))

---

## File Permissions Strategy (UID/GID)

TODO
