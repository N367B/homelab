# Day 0: Manual Bootstrap Guide

The strictly manual steps to take each baremetal node from "powered off, blank disk" to "ready for Ansible". Anything beyond this file is handled by Ansible, OpenTofu, or Docker Compose.

Both nodes run Debian 13 Trixie on a BTRFS root. The root stays on the `@rootfs` subvolume the Debian installer creates, and snapper takes a snapshot before and after each apt run where `snapper_root` is enabled (compute today). The hosts are rebuilt from this repo, so there is no wider subvolume layout and no grub-btrfs boot menu.

---

## Server 1 (HP ML350 Gen9)

Everything here is done from the iLO remote console (`https://192.168.7.3`), so nothing needs a screen or a keyboard on the server.

### 1. BIOS and iLO

Set in the RBSU (F9 at POST):

- Boot mode UEFI, no legacy boot.
- Secure Boot off. ZFS and the NVIDIA driver are DKMS modules that are not signed, and a Secure Boot kernel refuses to load them. It is off today.
- The embedded SATA controller in AHCI mode, not Smart Array. Check this setting first. The POST logs `1785-Slot 0 Drive Array Not Configured` on every boot, a sign the B140i Smart Array firmware still scans the SATA ports.
- PXE and option ROMs off on the four unused LOM ports (`eno1`-`eno4`). This shortens POST, which takes about 3.5 minutes from power on to SSH today.
- Power on after a power loss: restore the last power state.
- ASR (Automatic Server Recovery) stays enabled. It rebooted the node after the October 2026 memory error instead of leaving it hung.

iLO:

- Static IP `192.168.7.3`, strong password (stored in Proton Pass).
- iLO account `fanctl` with its SSH key, used by the cooling role and the IML watcher on the edge. It survives an OS reinstall but not an iLO factory reset (see `cooling.md`).

Wake-on-LAN does not work on this node. The X520 reports `Supports Wake-on: d` and the LOM ports that support it are not cabled. The node is powered on through the iLO (`start /system1` in its SSH CLI, or the power button of the web UI) or with the front button.

### 2. Know the disks

The `sdX` letters change between boots on this machine (the SSDs were `sdc`/`sdg` one day and `sda`/`sdh` the next). Always identify disks by model and serial number, never by letter.

| Disks | Model | Identify by |
| --- | --- | --- |
| System SSDs | 2 x Samsung PM863a 240 GB (`MZ7LM240HMHQ`) | serials `S2TWNX0J800659` and `S2TWNX0J802922`, 223.6 GiB |
| Bulk pool | 6 x HGST HUH721010AL42C0 10 TB SAS, behind the LSI HBA | `wwn-0x5000cca2...`, 9.1 TiB |
| Fast pool | Samsung PM9A1a and WD SN750, 1 TB NVMe | `nvme0n1` / `nvme1n1` |
| iLO virtual media | `LUN 00 Media 0`, 512 MB | not a disk, never pick it |

### 3. OS install (Debian 13 netinst)

Download the current Debian 13 `amd64` netinst ISO from <https://www.debian.org/distrib/netinst>. In the iLO HTML5 console, mount it with `Virtual Drives` > `Image File CD-ROM/DVD`, then pick the virtual CD in the one-time boot menu (F11 at POST). Use the graphical or text `Install` entry. The installer needs internet, so let it take a DHCP lease on the X520 (`ens3`) when it asks for the primary interface.

The SSDs still carry signatures from earlier installs (ZFS labels, an mdadm array, ext4). Clear them before partitioning, otherwise the installer may assemble the old array. Open a shell (`Execute a shell` in the installer menu, or Alt+F2) once the disks are detected:

```sh
ls -l /dev/disk/by-id/ | grep S2TWNX0J      # find the two SSD letters
cat /proc/mdstat                            # any old array shows here
mdadm --stop --scan                         # stops all of them
wipefs -a /dev/sdX2 /dev/sdX1 /dev/sdX      # both SSDs, partitions first
```

Hostname `compute`, domain empty, user `noe`. Leave the root password empty, so the installer gives `noe` sudo rights. Identical layout on both SSDs:

| Partition | Size  | Type       | Purpose      |
| --------- | ----- | ---------- | ------------ |
| `p1`      | 1 GiB | EFI System | ESP (FAT32)  |
| `p2`      | rest  | BTRFS      | RAID1 member |

The Debian installer does not handle multi-device BTRFS, so RAID1 is reached in two steps: install on one SSD, convert on first boot.

- On the first SSD, use `p1` as the ESP and format `p2` as BTRFS mounted at `/`.
- On the second SSD, create the same partitions and leave `p2` unused. Its `p1` becomes the second ESP after the first boot.
- Do not touch the HGST and NVMe disks. The ZFS role handles them.

Answer `No` when the installer warns that there is no swap partition. Swap is zram, set up by Ansible.

Software selection: `SSH server` and `standard system utilities` only. No desktop.

### 4. First boot (iLO console)

```sh
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y python3 python3-apt
```

Reboot if the upgrade installed a new kernel. DKMS builds ZFS and the NVIDIA driver for the installed kernels, and the first Ansible run loads ZFS in the running one.

`sudo` comes with the empty root password. `python3` (module interpreter) and `python3-apt` (the `apt` module) are what Ansible needs. Everything else, including the extra Debian components, ZFS, the NVIDIA driver and Incus, comes from Ansible. On the admin workstation, install `sops` from <https://github.com/getsops/sops/releases>.

#### Static IP

The X520 in PCIe slot 3 is `ens3`. Give it the fixed address in `/etc/network/interfaces`, so Ansible can reach it and it stays outside the Freebox DHCP pool (`192.168.7.150` - `192.168.7.250`):

```sh
allow-hotplug ens3
iface ens3 inet static
    address 192.168.7.11/24
    gateway 192.168.7.1
    dns-nameservers 192.168.7.1
```

The mask is `/24` because the Freebox serves a fixed `/24` and is the only router (see `network.md`). Apply with `sudo systemctl restart networking` or reboot. The Ansible role `network` takes it over on the first run and moves the stanza to `/etc/network/interfaces.d/lan`.

#### BTRFS RAID1

```sh
sudo btrfs device add /dev/disk/by-id/ata-SAMSUNG_MZ7LM240HMHQ-00005_<second-serial>-part2 /
sudo btrfs balance start -dconvert=raid1 -mconvert=raid1 /
sudo btrfs filesystem usage /   # Data, Metadata and System all RAID1, no single chunks
```

> Degraded boot note: if one SSD dies later, the system will not mount root automatically. At the GRUB prompt (iLO console), edit the kernel line and append `rootflags=degraded` to boot on the surviving disk, then replace the drive (`btrfs replace`). This is the accepted tradeoff for checksum self-healing. See `storage.md`.

#### Second ESP

GRUB only goes to the first SSD. Copy it to the second ESP and add a firmware boot entry, so either SSD can boot alone:

```sh
sudo mkfs.vfat -F 32 /dev/disk/by-id/ata-SAMSUNG_MZ7LM240HMHQ-00005_<second-serial>-part1
sudo mount /dev/disk/by-id/ata-SAMSUNG_MZ7LM240HMHQ-00005_<second-serial>-part1 /mnt
sudo cp -a /boot/efi/EFI /mnt/ && sudo umount /mnt
sudo efibootmgr --create --disk /dev/disk/by-id/ata-SAMSUNG_MZ7LM240HMHQ-00005_<second-serial> --part 1 --label "debian (ssd 2)" --loader '\EFI\debian\shimx64.efi'
sudo efibootmgr -v                     # two debian entries, one per SSD
```

A GRUB package update only rewrites the first ESP. Repeat the copy after one until the baseline role keeps both in sync (see `todo.md`).

### 5. Key injection (from admin workstation)

```sh
ssh-copy-id -i ~/.ssh/homelab.pub noe@192.168.7.11
```

The age key stays on the admin workstation: Ansible decrypts the secrets there and sends only the rendered values (see `secrets.md`).

### 6. First Ansible run

```sh
make deploy-first LIMIT=compute
```

It installs the baseline, the network files, monitoring, ZFS and the pools, the NVIDIA driver, Incus with its preseed, and the cooling agent. It asks for the sudo password once and sets up passwordless sudo, so later runs use `make deploy LIMIT=compute`.

### 7. Old ZFS pools

The ZFS role creates the pools when they are missing and never forces anything. If the disks still hold a pool with the same name from an earlier install, the role stops with a message. `zpool create` also refuses disks that belong to another pool. ZFS is installed at that point, so the old pools can be dealt with right away.

To keep a pool, import it (`sudo zpool import <name>`) and the role adopts it. To start empty, destroy the old pools. This erases their data.

```sh
sudo zpool import                              # lists the old pools and their disks
sudo zpool import -f <name> && sudo zpool destroy <name>
```

If `zpool create` still refuses a disk because of an old label, check its serial and clear it with `sudo zpool labelclear -f /dev/disk/by-id/<disk>`. Then run `make deploy LIMIT=compute` again.

### 8. Reboot and check

Reboot once after the first complete run, for the NVIDIA driver and the `ens3` stanza in `interfaces.d/lan`.

Checks after the reboot:

```sh
sudo btrfs filesystem usage /          # RAID1 everywhere
sudo snapper list                      # config root exists
zpool status && zpool get ashift       # fast and bulk ONLINE, ashift 12
incus list && incus network show incusbr0
nvidia-smi
systemctl status ml350-fans-agent smartmontools rasdaemon homelab-edac-check.timer homelab-boot-check.timer
```

Ansible takes over from here.

---

## Server 2 (AM06 Pro)

### 1. OS install

- Boot mode: UEFI
- Hostname: `edge`
- Single drive partitioning on `/dev/nvme0n1`:
  - `nvme0n1p1` 1 GiB ESP (FAT32)
  - `nvme0n1p2` rest, single BTRFS partition mounted at `/` (the installer puts it in the `@rootfs` subvolume)
- Software selection: same as Server 1 (minimal + SSH server)
- Console fallback: HDMI + USB keyboard. Built-in WiFi is configured as a network fallback (config TBD).

### 2. First boot + key injection

Same as Server 1 steps 4 and 5, but skip the RAID1 conversion and the second ESP because this node has a single drive. The LAN interface is `enp4s0` and the address `192.168.7.10`.

---

## Decisions

- Admin username: `noe` on both nodes, key-only SSH, passwordless sudo
- Hostnames: `compute` (Server 1) and `edge` (Server 2), matching the DNS names in `network.md`

## Open items

- Exact wifi-fallback config on Server 2
