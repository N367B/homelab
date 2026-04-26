# Network Plan

Overall network: `10.0.0.0/8`

Public addresses are intentionally not tracked here. They change over time and do not need to live in the repo.

---

## Current Network Model

For now this is a flat LAN with no VLAN separation. The ranges below are allocation conventions inside the broader `10.0.0.0/8` plan.

The goal is to keep addressing easy to remember now while reserving a clean path to VLANs or routed subnets later. Until VLANs/routing exist, these ranges do not provide isolation by themselves.

## Subnet Plan

Range | Name | Purpose | Status
--- | --- | --- | ---
`10.0.0.0/16` | Core infrastructure | Gateway, switch, iLO, edge services, ingress, DNS, DHCP | Locked
`10.10.0.0/16` | Homelab | Compute host, Incus, VMs, Docker application endpoints | Locked
`10.20.0.0/16` | IoT | Shelly plugs, relays, smart devices | Locked
`10.32.0.0/12` | DHCP clients | Normal clients, Wi-Fi devices, temporary machines | Locked

## Locked Addresses

IP / Range | Name | Role
--- | --- | ---
`10.0.0.1` | `gateway` | Livebox / default gateway
`10.0.0.2` | `switch` | Main switch management
`10.0.0.3` | `compute-ilo` | Server 1 iLO
`10.0.0.10` | `edge` | Server 2 / DNS / DHCP / ingress
`10.10.10.10` | `compute` | Server 1 / main baremetal host
`10.10.20.0/24` | `incus` | Incus system containers
`10.10.30.0/24` | `vms` | Virtual machines
`10.10.40.0/24` | `apps` | Docker application endpoints / routed service IPs
`10.20.1.10` | `shellyplug-1` | Power monitoring / control
`10.20.1.11` | `shellyplug-2` | Power monitoring / control

## DNS and Domains

Domain | Provider | Purpose
--- | --- | ---
`{{ homelab_domain }}` | Cloudflare | Public homelab domain
`{{ secondary_domain }}` | Porkbun | Owned, purpose TBD

Public DNS target:

- `{{ homelab_domain }}`
- `*.{{ homelab_domain }}`

Cloudflare must stay DNS-only. No Cloudflare proxying.

Public records should point to the home connection. Because the public IP may be dynamic, DDNS is required.

DDNS target:

- Runs as a Docker Compose service.
- Runs on the edge node once the edge node exists.
- Updates Cloudflare records for `{{ homelab_domain }}`.
- Specific DDNS image/tool is TBD.
- Provider API credentials are stored through SOPS.

Internal DNS should use the same service names where possible. For example, `photos.{{ homelab_domain }}` should resolve internally to the LAN ingress address instead of forcing local clients out through public DNS and hairpin NAT.

## DHCP and Local DNS

Current state:

- Livebox handles DHCP and DNS.
- The Livebox already supports the planned `10.0.0.0/8` network.

Target state:

- AdGuard Home replaces Livebox DHCP.
- AdGuard Home replaces Livebox DNS for clients.
- AdGuard Home owns local DNS overrides for known IPs and internal-only records.
- Livebox remains the default gateway unless that changes later.

## Public Entrypoint

Public traffic enters through the edge node first.

- Public `80/tcp` and `443/tcp` forward from Livebox to `10.0.0.10`.
- Non-HTTP public ports also enter through the edge node first when practical.

Entrypoint address:

- `10.0.0.10`: edge node

Note: the edge node has a 2.5G NIC while the main network is 10G and the internet connection is up to 8G. The single-entrypoint model is still preferred because it is simpler and safer. Revisit only if throughput becomes a real limit.

## Public vs Internal Services

Some services are expected to be publicly reachable, for example:

Service | Example domain | Initial exposure
--- | --- | ---
Jellyfin | `jellyfin.{{ homelab_domain }}` | Public candidate
Immich | `photos.{{ homelab_domain }}` | Public candidate
Nextcloud | `cloud.{{ homelab_domain }}` | Public candidate

Admin and infrastructure tools should default to internal-only or VPN-only.

Final exposure policy should eventually live close to the service definitions, so routing and documentation can be generated or checked from one source of truth.

## Non-HTTP Traffic

For game servers or proprietary protocols, forward the public port to the edge node first, then forward/NAT to the service host if needed. Direct forwarding to compute is an exception, not the default.

## Split-Horizon DNS

Target behavior:

- External clients resolve public services to the home public address.
- Internal LAN or VPN clients resolve the same names to the internal ingress address.
- Internal-only services resolve only inside AdGuard Home.

This avoids relying on hairpin NAT and keeps local traffic local.

## IPv6 Notes

IPv6 service exposure is deferred.

Before enabling public `AAAA` records for services, firewall behavior must be verified on the edge node, the ISP box, and the hosts themselves. IPv6 does not rely on NAT for safety.

Longer-term goal:

- Stop relying on Livebox IPv6 Router Advertisements if they prevent custom DNS control.
- Have the edge node provide controlled IPv6 RA with custom DNS.

## Wake-on-LAN

Wake-on-LAN is required for Server 1 because it may be powered down when not needed.

Requirements:

- Server 1 BIOS/iLO WoL enabled.
- OS NIC WoL enabled and persisted by Ansible.
- Edge node can send the magic packet.
- Optional UI/API endpoint later, protected behind VPN or SSO.

---

<details>
  <summary>Obsolete Network</summary>

## Obsolete Network

Local subnet: `192.168.1.0/24`

Range | Purpose
--- | ---
`192.168.1.0` to `192.168.1.20` | Core infrastructure and management
`192.168.1.11` to `192.168.1.99` | DHCP pool
`192.168.1.100` to `192.168.1.199` | Reserved homelab static range
`192.168.1.200` to `192.168.1.255` | Reserved miscellaneous

Old allocations:

IP | Role
--- | ---
`192.168.1.1` | Gateway
`192.168.1.7` | iLO
`192.168.1.100` | Baremetal IP
`192.168.1.251` | ShellyPlug 1
`192.168.1.252` | ShellyPlug 2
`192.168.1.254` | Switch

</details>
