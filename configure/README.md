# configure/ — Ansible

OS-level configuration for both nodes. Run interactively from the admin
workstation; scheduled `--check` drift detection runs from the edge controller
container (TBD).

## Usage

```sh
cd configure
ansible-galaxy collection install -r requirements.yml
ansible-playbook site.yml                  # converge everything
ansible-playbook site.yml --limit edge     # edge only
ansible-playbook site.yml --check --diff   # drift detection
```

## Layout

| Path | Purpose |
| --- | --- |
| `site.yml` | Entry point — baseline everywhere, then per-group roles |
| `inventory/hosts.yml` | The two nodes (`edge`, `compute`) |
| `group_vars/` | Shared vars + per-group firewall ports |
| `roles/baseline` | Hostname, packages, SSH hardening, nftables, zram, scrub timer, unattended-upgrades |
| `roles/docker_host` | Docker engine + compose plugin from the official repo |

## TODO

- `baseline`: BTRFS subvolume layout + snapper + upstream grub-btrfs install task (see comment in the role)
- `docker_host`: deploy compose stacks from `apps/` with sops-rendered env files
- `incus_host` role for the compute node
- WireGuard role for the edge node
