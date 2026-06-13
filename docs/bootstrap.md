# Day 0: Manual Bootstrap Guide

The strictly manual steps to take each baremetal node from "powered off, blank disk" to "ready for Ansible". Anything beyond this file is handled declaratively by Ansible / OpenTofu / Docker compose.

Both nodes run **Debian 13 (Trixie)** with **BTRFS** root and `snapper` for upgrade snapshots. `grub-btrfs` boot menu integration is planned but not implemented until its upstream install task exists.

---

## Server 1 (HP ML350 Gen9)

### 1. BIOS & iLO

- Boot mode: **UEFI** (CSM disabled)
- Wake-on-LAN: **enabled** for the primary NIC
- iLO: static IP `10.0.0.3`, strong password (stored in Proton Pass)

### 2. OS install (Debian 13 netinst, manual partitioning)

Hostname: `compute`. Identical layout on both 240 GB SSDs (`/dev/sda`, `/dev/sdb`):

| Partition | Size  | Type           | Purpose          |
| --------- | ----- | -------------- | ---------------- |
| `sdX1`    | 1 GiB | EFI System     | ESP (FAT32)      |
| `sdX2`    | rest  | BTRFS          | RAID1 member     |

The Debian installer does not handle multi-device BTRFS, so RAID1 is reached in two steps: install on one disk, convert on first boot.

In the installer:

- Partition **both** disks with the layout above (so they stay identical)
- Format `sda2` as BTRFS mounted at `/` — leave `sdb2` untouched for now
- Mount `sda1` at `/boot/efi`; `sdb1` stays as a sync target (handled later by Ansible)
- Install GRUB to `/dev/sda` (the second ESP is populated by Ansible)

The full subvolume layout (`@`, `@home`, `@var`, `@log`, `@snapshots`) is created by Ansible on first run, not by the installer — keeps the manual step short and the layout defined declaratively.

Software selection: minimal install + `standard system utilities` + `SSH server`. No desktop.

### 3. First boot (root over console)

```sh
apt update && apt full-upgrade -y
apt install -y sudo git python3 age chrony zram-tools snapper btrfs-progs
```

Note: `sops` and `grub-btrfs` come from upstream releases because neither is packaged in Debian 13/Trixie. `sops` is installed by Ansible from the Renovate-managed GitHub release declared in `configure/group_vars/all.yml`; `grub-btrfs` still needs an explicit upstream install task before rollback boot entries are implemented. On the admin workstation, install `sops` from <https://github.com/getsops/sops/releases>.

Convert the root filesystem to BTRFS native RAID1 (one-time, ~minutes on a fresh install):

```sh
btrfs device add /dev/sdb2 /
btrfs balance start -dconvert=raid1 -mconvert=raid1 /
btrfs filesystem usage /   # verify: Data,RAID1 / Metadata,RAID1 / System,RAID1
```

> Degraded boot note: if one SSD dies later, the system will not mount root automatically. At the GRUB prompt, edit the kernel line and append `rootflags=degraded` to boot on the surviving disk, then replace the drive (`btrfs replace`). This is the accepted tradeoff for checksum self-healing — see `storage.md`.

Create the admin user `noe`, add to `sudo`:

```sh
adduser noe
usermod -aG sudo noe
```

Sudo policy: passwordless for `noe` (`echo 'noe ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/noe`). SSH is key-only and password auth is disabled by Ansible, so the account is only reachable with the private key; passwordless sudo keeps Ansible runs and the scheduled drift checks friction-free.

### 4. Key injection (from admin workstation)

```sh
ssh-copy-id -i ~/.ssh/id_ed25519.pub noe@10.10.10.10
scp ~/.config/sops/age/keys.txt noe@10.10.10.10:/tmp/age.key
```

On the host, move the age key into place (mode 600, owned by the user that will run Ansible):

```sh
install -m 600 -o noe -g noe -D /tmp/age.key ~/.config/sops/age/keys.txt
shred -u /tmp/age.key
```

Ansible takes over from here.

---

## Server 2 (AM06 Pro)

### 1. OS install

- Boot mode: UEFI
- Hostname: `edge`
- Single drive partitioning on `/dev/nvme0n1`:
  - `nvme0n1p1` 1 GiB ESP (FAT32)
  - `nvme0n1p2` rest, single BTRFS partition mounted at `/` (subvolumes created by Ansible on first run, same model as Server 1)
- Software selection: same as Server 1 (minimal + SSH server)
- Console fallback: HDMI + USB keyboard. Built-in WiFi is configured as a network fallback (config TBD).

### 2. First boot + key injection

Same as Server 1 steps 3 and 4 (skip the RAID1 conversion — single drive), with the host reachable at its planned edge IP `10.0.0.10`.

---

## Decisions

- Admin username: `noe` on both nodes, key-only SSH, passwordless sudo
- Hostnames: `compute` (Server 1) and `edge` (Server 2) — matching the DNS names in `network.md`

## Open items

- Exact wifi-fallback config on Server 2
