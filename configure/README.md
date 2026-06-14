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

### Running from WSL on `/mnt/c`

The Windows drive is mounted world-writable, so Ansible silently ignores
`ansible.cfg` there (and with it the inventory path), leaving no hosts to
match. Point at the config explicitly so it is honored:

```sh
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
ansible-playbook site.yml --limit edge -K
```

Permanent alternative: make `/mnt/c` non-world-writable via `/etc/wsl.conf`
(`[automount]\noptions = "metadata,umask=22,fmask=11"`) then `wsl --shutdown`.

## Layout

| Path | Purpose |
| --- | --- |
| `site.yml` | Entry point — baseline everywhere, then per-group roles |
| `inventory/hosts.yml` | The two nodes (`edge`, `compute`) |
| `group_vars/` | Shared vars + per-group firewall ports |
| `roles/baseline` | Hostname, packages, SSH hardening, nftables, zram, scrub timer, unattended-upgrades |
| `roles/docker_host` | Docker engine + compose plugin from the official repo |
| `roles/compose_stacks` | Deploys `apps/` stacks to `/opt/stacks/` with sops-rendered `.env` (decrypted on the controller) |

## TODO

- `baseline`: BTRFS subvolume layout + snapper + upstream grub-btrfs install task (see comment in the role)
- `incus_host` role for the compute node
- WireGuard role for the edge node
