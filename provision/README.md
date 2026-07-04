# provision/ OpenTofu

OpenTofu configuration for Incus system containers and VMs on the compute node. Planned scope includes `production` and `testing` workspaces, networks, and profiles.

Empty until the Server 1 build starts. Planned providers:

- `lxc/incus` for containers, profiles, and networks
- `carlpett/sops` for secrets from `secrets/*.sops.yaml`
