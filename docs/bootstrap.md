# Day 0: Manual Bootstrap Guide

The strictly manual steps to take each baremetal node from "powered off, blank disk" to "ready for Ansible". Anything beyond this file is handled declaratively by Ansible / OpenTofu / Docker compose.

Both nodes run **Debian 13 (Trixie)** with **BTRFS** root and `snapper` + `grub-btrfs` for upgrade rollback.

---

## Server 1 (HP ML350 Gen9)

### 1. BIOS & iLO

- Boot mode: **UEFI** (CSM disabled)
- Wake-on-LAN: **enabled** for the primary NIC
- iLO: static IP `10.0.0.3`, strong password (stored in Proton Pass)

### 2. OS install (Debian 13 netinst, manual partitioning)

Identical layout on both 240 GB SSDs (`/dev/sda`, `/dev/sdb`):

| Partition | Size  | Type           | Purpose          |
| --------- | ----- | -------------- | ---------------- |
| `sdX1`    | 1 GiB | EFI System     | ESP (FAT32)      |
| `sdX2`    | rest  | Linux RAID     | mdadm member     |

In the installer:

- Assemble `/dev/md0` as RAID1 over `sda2` + `sdb2` (metadata 1.2)
- Format `/dev/md0` as a single BTRFS partition mounted at `/`
- Mount `sda1` at `/boot/efi`; `sdb1` stays as a sync target (handled later by Ansible)
- Install GRUB to **both** `/dev/sda` and `/dev/sdb`

The full subvolume layout (`@`, `@home`, `@var`, `@log`, `@snapshots`) is created by Ansible on first run, not by the installer — keeps the manual step short and the layout defined declaratively.

Software selection: minimal install + `standard system utilities` + `SSH server`. No desktop.

### 3. First boot (root over console)

```sh
apt update && apt full-upgrade -y
apt install -y sudo git python3 age sops chrony zram-tools snapper grub-btrfs btrfs-progs mdadm
```

Create the admin user (name TBD), add to `sudo`:

```sh
adduser <username>
usermod -aG sudo <username>
```

### 4. Key injection (from admin workstation)

```sh
ssh-copy-id -i ~/.ssh/id_ed25519.pub <username>@10.10.10.10
scp ~/.config/sops/age/keys.txt <username>@10.10.10.10:/tmp/age.key
```

On the host, move the age key into place (mode 600, owned by the user that will run Ansible):

```sh
install -m 600 -o <username> -g <username> /tmp/age.key ~/.config/sops/age/keys.txt
shred -u /tmp/age.key
```

Ansible takes over from here.

---

## Server 2 (AM06 Pro)

### 1. OS install

- Boot mode: UEFI
- Single drive partitioning on `/dev/nvme0n1`:
  - `nvme0n1p1` 1 GiB ESP (FAT32)
  - `nvme0n1p2` rest, single BTRFS partition mounted at `/` (subvolumes created by Ansible on first run, same model as Server 1)
- Software selection: same as Server 1 (minimal + SSH server)
- Console fallback: HDMI + USB keyboard. Built-in WiFi is configured as a network fallback (config TBD).

### 2. First boot + key injection

Same as Server 1 steps 3 and 4, with the host reachable at its planned edge IP.

---

## Open items

- Final admin username + sudo policy (passwordless? password-required for sudo?)
- Hostname convention (`compute01` / `edge01`? something else?)
- Exact wifi-fallback config on Server 2
