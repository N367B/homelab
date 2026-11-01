# configure/ Ansible

OS-level configuration for both nodes. I run it interactively from the admin workstation. Scheduled `--check` drift detection will run from the edge controller container once monitoring automation is in place.

## Usage

```sh
cd configure
ansible-galaxy collection install -r requirements.yml
ansible-playbook site.yml                  # converge everything
ansible-playbook site.yml --limit edge     # edge only
ansible-playbook site.yml --check --diff   # drift detection
```

### Running from WSL on `/mnt/c`

The Windows drive is mounted world-writable, so Ansible silently ignores `ansible.cfg` there (and with it the inventory path), leaving no hosts to match. Point at the config explicitly so it is honored:

```sh
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
ansible-playbook site.yml --limit edge -K
```

Permanent alternative: make `/mnt/c` non-world-writable via `/etc/wsl.conf` (`[automount]\noptions = "metadata,umask=22,fmask=11"`) then `wsl --shutdown`.

## Layout

| Path | Purpose |
| --- | --- |
| `site.yml` | Entry point. Baseline everywhere, then per-group roles |
| `inventory/hosts.yml` | The two nodes (`edge`, `compute`) |
| `group_vars/` | Shared vars + per-group firewall ports |
| `roles/baseline` | Hostname, packages, SSH hardening, nftables, zram, scrub timer, unattended-upgrades, snapper on `/` where enabled |
| `roles/network` | Static LAN address in `/etc/network/interfaces.d/lan` |
| `roles/docker_host` | Docker engine + compose plugin from the official repo. Edge only |
| `roles/compose_stacks` | Deploys `apps/` stacks to `/opt/stacks/` with sops-rendered `.env` (decrypted on the controller) |
| `roles/edge_backup` | Restic backups of the edge, local and offsite |
| `roles/wireguard` | WireGuard remote access on the edge |
| `roles/nut` | NUT reads the UPS over USB on the edge |
| `roles/ml350_fans` | ML350 cooling through the modded iLO (see `docs/cooling.md`) |
| `roles/monitoring_base` | smartd, rasdaemon, EDAC memory error check and the `homelab-notify` alert script |
| `roles/ilo_watch` | Edge timer that reads the iLO IML and alerts on new Critical or Caution entries |
| `roles/zfs` | OpenZFS, pool creation (never forced), datasets, ARC cap, monthly scrubs, ZED. Compute only |
| `roles/nvidia` | NVIDIA driver from Debian non-free. Compute only |
| `roles/incus_host` | Incus 7.0 LTS from Zabbly and its one-time preseed (bridge, storage pool, default profile). Compute only |

## Roadmap

- `baseline`: second ESP sync and GRUB on both SSDs of the compute node
- Power schedule of the compute node through the iLO, driven by the edge
