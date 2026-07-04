# Day 0: Manual Bootstrap Guide

The strictly manual steps to take each baremetal node from "powered off, blank disk" to "ready for Ansible". Anything beyond this file is handled by Ansible, OpenTofu, or Docker Compose.

Both nodes run Debian 13 Trixie with BTRFS root and `snapper` for upgrade snapshots. `grub-btrfs` boot menu integration is planned but not implemented until its upstream install task exists.

---

## Server 1 (HP ML350 Gen9)

### 1. BIOS & iLO

- Boot mode: UEFI, CSM disabled
- Wake-on-LAN: enabled for the primary NIC
- iLO: static IP `10.0.0.3`, strong password (stored in Proton Pass)

### 2. OS install (Debian 13 netinst, manual partitioning)

Hostname: `compute`. Identical layout on both 240 GB SSDs (`/dev/sda`, `/dev/sdb`):

| Partition | Size  | Type       | Purpose      |
| --------- | ----- | ---------- | ------------ |
| `sdX1`    | 1 GiB | EFI System | ESP (FAT32)  |
| `sdX2`    | rest  | BTRFS      | RAID1 member |

The Debian installer does not handle multi-device BTRFS, so RAID1 is reached in two steps: install on one disk, convert on first boot.

In the installer:

- Partition both disks with the layout above so they stay identical
- Format `sda2` as BTRFS mounted at `/`. Leave `sdb2` untouched for now
- Mount `sda1` at `/boot/efi`. `sdb1` stays as a sync target, handled later by Ansible
- Install GRUB to `/dev/sda` (the second ESP is populated by Ansible)

The full subvolume layout (`@`, `@home`, `@var`, `@log`, `@snapshots`) is created by Ansible on first run, not by the installer. This keeps the manual step short and the layout in the repo.

Software selection: minimal install + `standard system utilities` + `SSH server`. No desktop.

### 3. First boot (root over console)

This step only does the bare minimum to let Ansible take over: a static IP, the few packages Ansible itself needs, an admin user, and the keys. Everything else, including the full package set, hardening, zram, sops, scrub, and Docker, is installed by Ansible.

```sh
apt update && apt full-upgrade -y
apt install -y sudo python3 python3-apt
```

`sudo` (for Ansible `become`), `python3` (module interpreter) and `python3-apt` (the `apt` module) are the only packages Ansible needs to connect and bootstrap. The full baseline set, including `git`, `chrony`, `zram-tools`, `snapper`, `btrfs-progs`, `nftables`, `age`, and `unattended-upgrades`, is in `configure/group_vars/all.yml` and installed by the baseline role. `sops` and `grub-btrfs` are not in Debian. `sops` is installed by Ansible from the Renovate-managed GitHub release. `grub-btrfs` still needs an upstream install task. On the admin workstation, install `sops` from <https://github.com/getsops/sops/releases>.

#### Static IP

The node defaults to DHCP. Give it its fixed address so Ansible can reach it reliably, and because the edge will later run DHCP itself. Find the interface name with `ip -br a`, then write `/etc/network/interfaces.d/static`:

```sh
auto <iface>
iface <iface> inet static
    address 10.0.0.10/8
    gateway 10.0.0.1
    dns-nameservers 10.0.0.1
```

The mask is `/8` because the network is flat for now, with no VLANs yet. All nodes share one subnet and reach each other directly at L2. The `/16` ranges in `network.md` are future allocation conventions for when VLANs or routing exist, not the current mask. Address is per node, with edge at `10.0.0.10/8` and compute at `10.10.10.10/8`, both using gateway `10.0.0.1`. Apply with `systemctl restart networking` or reboot. Ansible can take over this file later.

Convert the root filesystem to BTRFS native RAID1 (one-time, ~minutes on a fresh install):

```sh
btrfs device add /dev/sdb2 /
btrfs balance start -dconvert=raid1 -mconvert=raid1 /
btrfs filesystem usage /   # verify: Data,RAID1 / Metadata,RAID1 / System,RAID1
```

> Degraded boot note: if one SSD dies later, the system will not mount root automatically. At the GRUB prompt, edit the kernel line and append `rootflags=degraded` to boot on the surviving disk, then replace the drive (`btrfs replace`). This is the accepted tradeoff for checksum self-healing. See `storage.md`.

The `noe` user is created by the Debian installer. If a root password was set during install, `noe` is not in the `sudo` group yet. Add it. It already has its login password.

```sh
usermod -aG sudo noe
```

Passwordless sudo is set up by the baseline role (`/etc/sudoers.d/noe`), not by hand. So the first Ansible run uses the password you just set: `ansible-playbook site.yml --limit edge -K` (`-K` prompts once for the sudo password). After that run, NOPASSWD is in place and `-K` is no longer needed. SSH is also key-only after the first converge (password auth disabled), so the account is only reachable with the private key.

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

Same as Server 1 steps 3 and 4, but skip the RAID1 conversion because this node has a single drive. The host should be reachable at its planned edge IP `10.0.0.10`.

---

## Decisions

- Admin username: `noe` on both nodes, key-only SSH, passwordless sudo
- Hostnames: `compute` (Server 1) and `edge` (Server 2), matching the DNS names in `network.md`

## Open items

- Exact wifi-fallback config on Server 2
