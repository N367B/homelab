# provision/ — OpenTofu

Declarative management of Incus system containers and VMs on the compute node
(`production` / `testing` workspaces, networks, profiles).

Empty until the Server 1 build starts. Planned providers:

- `lxc/incus` — containers, profiles, networks
- `carlpett/sops` — secrets from `secrets/*.sops.yaml`
