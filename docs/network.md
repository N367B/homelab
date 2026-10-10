# Network Plan

The lab runs on one flat LAN, `192.168.7.0/24`, served by the Freebox. Containers, VMs and app endpoints live in `10.10.0.0/16`, routed by the compute node. WireGuard clients use `10.99.0.0/24`.

The earlier design used `10.0.0.0/8` split into one `/16` per purpose. It is kept in the history section at the bottom as the target for the day a dedicated router joins the lab.

Public addresses are not tracked here. They change over time and do not need to live in the repo.

The move from the previous network to this one is tracked in `network-migration.md`.

---

## Principles

- The Freebox is the single router, the Wi-Fi access point and the DHCP server. If the lab is down, Wi-Fi and internet keep working.
- The switch forwards frames at L2 and the edge node serves DNS, ingress and VPN. Neither carries routing for the household.
- Infrastructure has static addresses. Clients get a small DHCP pool. Containers and VMs sit in their own subnets, away from DHCP.
- Hosts use a `/24` mask. A wider mask would make them look for `10.x` addresses on the local wire instead of using the gateway or a route.

## The Freebox

The Freebox Ultra serves the LAN. What its UI and API offer, as read on the box:

| Setting | Value |
| --- | --- |
| LAN IP of the box | Any private address. DHCP follows it |
| LAN netmask | Fixed `/24` |
| Mode | Router (bridge exists, unused) |
| Static routes | Prefix + gateway pairs, set in the UI. The API has no endpoint for them |
| DHCP | Range and up to 4 DNS servers handed out |
| Configuration | Set by hand in Freebox OS, then exported. The API stays unused: it proved unreliable on this box |
| Segmentation | One flat LAN. VLANs belong to another device |
| WAN | FTTH, 8 Gbit/s symmetric |

The `192.168.7.0/24` block was chosen for its rarity. The usual home blocks (`192.168.0.x`, `192.168.1.x`, `10.0.0.x`) show up in hotels and at friends' places, and a VPN client there would see two networks with the same addresses.

## Subnets

| Range | Name | Purpose | Status |
| --- | --- | --- | --- |
| `192.168.7.0/24` | Main LAN | Freebox, switch, iLO, servers, fixed devices, DHCP clients | Locked |
| `10.10.20.0/24` | Incus | System containers, routed by compute | Locked, not deployed |
| `10.10.30.0/24` | VMs | Virtual machines, routed by compute | Locked, not deployed |
| `10.10.40.0/24` | Apps | Docker endpoints and routed service IPs, routed by compute | Locked, not deployed |
| `10.99.0.0/24` | VPN | WireGuard remote access clients | Locked |
| `10.0.0.0/16` | Former core | Kept free, matches the history section | Reserved |

The `10.10.x.x` subnets are reached through two static routes, both still to be tested with a real routed subnet:

- On the Freebox: `10.10.0.0/16` via the compute node (`192.168.7.11`).
- On the edge node, owned by Ansible: the same route, so Caddy talks to containers directly on the wire instead of looping through the Freebox.

They exist while compute is powered on.

## Main LAN Address Map

| Range | Purpose |
| --- | --- |
| `192.168.7.1` | Freebox (gateway) |
| `192.168.7.2` - `.9` | Network gear: switch, iLO, future access points |
| `192.168.7.10` - `.19` | Core servers |
| `192.168.7.20` - `.49` | Fixed smart devices (Shelly plugs, relays) |
| `192.168.7.50` - `.149` | Reserved for future fixed hosts |
| `192.168.7.150` - `.250` | DHCP pool, 101 leases: phones, tablets, PCs, console, TV, Freebox Players, guests |
| `192.168.7.251` - `.254` | Reserved |

The pool covers one household (about ten devices today) plus guests. Everything else has a fixed address.

## Locked Addresses

| IP / Range | Name | Role |
| --- | --- | --- |
| `192.168.7.1` | `gateway` | Freebox Ultra: router, Wi-Fi, DHCP, default gateway |
| `192.168.7.2` | `switch` | XikeStor SKS8300-8X management, L2 |
| `192.168.7.3` | `compute-ilo` | Server 1 iLO |
| `192.168.7.10` | `edge` | Server 2 / DNS / ingress / VPN |
| `192.168.7.11` | `compute` | Server 1 / main baremetal host, routes the `10.10.x.x` subnets |
| `192.168.7.20` | `shellyplug-1` | Power monitoring / control |
| `192.168.7.21` | `shellyplug-2` | Power monitoring / control |
| `10.99.0.0/24` | `vpn` | WireGuard remote access clients |

## Open Items

Listed here so they stay visible.

- [ ] Static route `10.10.0.0/16` via compute on the Freebox, and a test of the return path with a real routed subnet
- [ ] The same route on the edge node (Ansible), and on the admin PC if it reaches containers directly
- [ ] Shelly plugs: fixed address on the device or a Freebox static lease. Freebox leases live outside git, so record them in this file
- [ ] Freebox IPv6 prefix firewall: turn it on, then open inbound ports one by one when a service needs them
- [ ] Freebox settings to review: remote API access, WAN ping reply, adblock, Wake-on-LAN, default SSID
- [ ] Throughput of the edge node (2.5G) against the 8G line (see Public Entrypoint)
- [ ] Switch hardening: admin account and telnet
- [ ] Fallback DNS handed out by DHCP (see DHCP and Local DNS)

## DNS and Domains

| Domain                   | Provider   | Purpose               |
| ------------------------ | ---------- | --------------------- |
| `{{ homelab_domain }}`   | Cloudflare | Public homelab domain |
| `{{ secondary_domain }}` | Porkbun    | Owned, purpose TBD    |

Public DNS target:

- `{{ homelab_domain }}` is the apex A record, kept current by DDNS.
- `*.{{ homelab_domain }}` is a static wildcard CNAME pointing at the apex, so per-service records follow the apex automatically and DDNS only has to manage one record.

Cloudflare must stay DNS-only. No Cloudflare proxying.

Public records should point to the home connection. Because the public IP may be dynamic, DDNS is required.

DDNS target:

- Runs as a Docker Compose service on the edge node (`apps/edge/ddns`).
- Current pick: `favonia/cloudflare-ddns` (pinned), updates the `{{ homelab_domain }}` apex A record.
- Cloudflare API token stored through SOPS.

Internal DNS should use the same service names where possible. For example, `photos.{{ homelab_domain }}` should resolve internally to the LAN ingress address instead of forcing local clients out through public DNS and hairpin NAT.

## DHCP and Local DNS

The Freebox serves DHCP, so every phone and TV keeps its lease when the edge node reboots.

| Setting | Value |
| --- | --- |
| Pool | `192.168.7.150` - `192.168.7.250` |
| Gateway | `192.168.7.1` |
| DNS handed out | `192.168.7.10` (AdGuard), then `192.168.7.1` (Freebox) as fallback |
| Leases | Sticky |

- AdGuard Home owns local DNS overrides for known IPs and internal-only records.
- The Freebox fallback keeps the internet working during an edge outage. Clients lose split-horizon names until the edge is back, and may pick the fallback now and then.
- The edge node resolves through the gateway plus a public resolver, as set in `group_vars/edge_nodes.yml`.

## Public Entrypoint

Public traffic enters through the edge node first.

- Public `80/tcp`, `443/tcp`, and `443/udp` forward from the Freebox to `192.168.7.10`. UDP 443 enables HTTP/3. Clients fall back to HTTP/2 over TCP when unavailable.
- Non-HTTP public ports also enter through the edge node first when practical.

Entrypoint address:

- `192.168.7.10`: edge node

Note: the edge node has a 2.5G NIC while the main network is 10G and the internet connection is up to 8G. The single-entrypoint model is still preferred because it is simpler and safer. Revisit only if throughput becomes a real limit.

## Public vs Internal Services

Some services are expected to be publicly reachable, for example:

| Service   | Example domain                  | Initial exposure |
| --------- | ------------------------------- | ---------------- |
| Jellyfin  | `jellyfin.{{ homelab_domain }}` | Public candidate |
| Immich    | `photos.{{ homelab_domain }}`   | Public candidate |
| Nextcloud | `cloud.{{ homelab_domain }}`    | Public candidate |

Admin and infrastructure tools (AdGuard, Dockge, the *arr stack, qBittorrent, Ollama API, ...) are internal-only / VPN-only. Their domains resolve via AdGuard split-horizon but get no public DNS record. See `services.md` for the per-service exposure table.

Final exposure policy should eventually live close to the service definitions, so routing and documentation can be checked from one place.

Raw application ports are not user-facing, even on the LAN. LAN clients should use service domains through Caddy. On the edge node, Caddy uses host networking and local services are reached over loopback. On compute, host firewalls should allow backend ports only from the edge node IP.

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

- Stop relying on Freebox IPv6 Router Advertisements if they prevent custom DNS control.
- Have the edge node provide controlled IPv6 RA with custom DNS.

## Wake-on-LAN

Wake-on-LAN is required for Server 1 because it may be powered down when not needed.

Requirements:

- Server 1 BIOS/iLO WoL enabled.
- OS NIC WoL enabled and persisted by Ansible.
- Edge node can send the magic packet.
- Optional UI/API endpoint later, protected behind VPN or SSO.

---

## History and Target

<details>
  <summary>Target design: routed /8 plan, for a dedicated router</summary>

This is the plan the lab used with the Livebox, and the layout to return to once a router that handles VLANs and inter-VLAN routing sits behind the Freebox. The whole lab lived in `10.0.0.0/8`, one `/16` per purpose.

| Range | Name | Purpose |
| --- | --- | --- |
| `10.0.0.0/16` | Core infrastructure | Gateway, switch, iLO, edge services, ingress, DNS, DHCP |
| `10.10.0.0/16` | Homelab | Compute host, Incus, VMs, Docker application endpoints |
| `10.20.0.0/16` | IoT | Shelly plugs, relays, smart devices |
| `10.32.0.0/12` | DHCP clients | Normal clients, Wi-Fi devices, temporary machines |

| IP / Range | Name | Role |
| --- | --- | --- |
| `10.0.0.1` | `gateway` | Livebox / default gateway |
| `10.0.0.2` | `switch` | Main switch management |
| `10.0.0.3` | `compute-ilo` | Server 1 iLO |
| `10.0.0.10` | `edge` | Server 2 / DNS / ingress |
| `10.10.10.10` | `compute` | Server 1 / main baremetal host |
| `10.10.20.0/24` | `incus` | Incus system containers |
| `10.10.30.0/24` | `vms` | Virtual machines |
| `10.10.40.0/24` | `apps` | Docker application endpoints / routed service IPs |
| `10.20.1.10` | `shellyplug-1` | Power monitoring / control |
| `10.20.1.11` | `shellyplug-2` | Power monitoring / control |
| `10.99.0.0/24` | `vpn` | WireGuard remote access clients |

Ways to get back to it, each adds one device to the path:

- A stable router behind the Freebox (MikroTik or a small OPNsense box) for VLANs and inter-VLAN routing, with a static route on the Freebox towards it.
- The XikeStor switch routing between VLANs. It is L3 capable and has a single power supply and no peer, and the routing is untested on this firmware. OpenWrt on its Realtek chip is expected to route in software.

The Freebox hands out 8 IPv6 `/64` prefixes with a configurable next hop, which is the way to give a downstream router or the compute node routed IPv6.

Freebox bridge mode would hand the public IP to one device and make it the router for the household. The edge node would then carry the whole connection.

</details>

<details>
  <summary>Previous networks</summary>

Orange Livebox with `10.0.0.0/8` (see the target design above), preceded by `192.168.1.0/24`.

Local subnet: `192.168.1.0/24`

| Range                              | Purpose                            |
| ---------------------------------- | ---------------------------------- |
| `192.168.1.0` to `192.168.1.20`    | Core infrastructure and management |
| `192.168.1.11` to `192.168.1.99`   | DHCP pool                          |
| `192.168.1.100` to `192.168.1.199` | Reserved homelab static range      |
| `192.168.1.200` to `192.168.1.255` | Reserved miscellaneous             |

Old allocations:

| IP              | Role         |
| --------------- | ------------ |
| `192.168.1.1`   | Gateway      |
| `192.168.1.7`   | iLO          |
| `192.168.1.100` | Baremetal IP |
| `192.168.1.251` | ShellyPlug 1 |
| `192.168.1.252` | ShellyPlug 2 |
| `192.168.1.254` | Switch       |

</details>
