# Migration to the Freebox LAN (`192.168.7.0/24`)

Temporary runbook. It is deleted once the migration is done and `network.md` is the only reference. The target is described in `network.md`.

## Ground rules

- The Freebox is configured by hand in Freebox OS and exported after each change. Nothing in this migration reads or writes it through the API.
- The workstation network (WSL and Windows) is configured through its own files (netplan). No step runs address commands on it.
- A device is changed only after the owner gives the go for that step, and each step says how it is checked and how it is undone.
- Every setting of the edge node ends up in the repo and is applied by Ansible. The switch is applied by a script that reads its settings from the repo.

## State on 2026-10-10

| Device | State |
| --- | --- |
| Freebox | Factory reset by the owner, then set up by hand: LAN `192.168.7.1/24`, DHCP pool `192.168.7.150` - `192.168.7.250`, Wi-Fi redone with eco mode off |
| Workstation | DHCP address `192.168.7.x` (WSL bridged) |
| Edge | `192.168.7.10/24`, gateway `192.168.7.1`, set by the role `network`. Internet, clock, DNS, AdGuard, WireGuard and a restic backup run (local and offsite) checked |
| Switch | `192.168.7.2/24`, default route `192.168.7.1`, saved in the startup-config, set by `scripts/switch/apply.py` |

## Target

| Device | Address | Set by |
| --- | --- | --- |
| Freebox | `192.168.7.1/24` | by hand, exported |
| Switch | `192.168.7.2/24`, default route `192.168.7.1` | `scripts/switch/apply.py`, values in `configure/group_vars/switch.yml` |
| Edge | `192.168.7.10/24`, gateway `192.168.7.1` | Ansible role `network`, values in `configure/group_vars/edge_nodes.yml` |

## Repo work (done on the branch)

- Every address in docs, inventory, `group_vars`, AdGuard template and examples is `192.168.7.x`.
- Role `network`: owns `/etc/network/interfaces` (loopback and an include) and `/etc/network/interfaces.d/lan` on the edge. It writes files and changes nothing live.
- `scripts/net-apply/apply.sh`: moves a node to the address already written on its disk. It arms a timer on the node that puts the old address back after 3 minutes, reloads the interface, then confirms from the new address. A wrong address reverts on its own.
- `scripts/switch/apply.py`: reads the switch, prints the differences (`make switch-check`) and applies them (`make switch`), then saves the configuration.

## Step 1: reach the edge and the switch

Both sat on `192.168.42.0/24` while the workstation is on `192.168.7.0/24`. They share the wire, so IPv6 link-local and the Freebox `/64` prefix reach them with no address on the workstation:

- Edge: SSH to its global IPv6 address, for example `make check LIMIT=edge EXTRA="-e ansible_host=<edge-ipv6>"`.
- Switch: `SWITCH_HOST='fe80::<eui64-of-its-mac>%eth0' make switch`. The address comes from the switch MAC with the universal/local bit flipped.

Console access works too (HDMI and keyboard on the edge, the console cable on the switch).

## Step 2: edge

From the workstation:

1. `make check LIMIT=edge EXTRA="--tags network -e ansible_host=<edge-ipv6>"`, then the same with `make deploy`. This writes the two interface files and leaves the live address alone.
2. `scripts/net-apply/apply.sh noe@<edge-ipv6> noe@192.168.7.10 enp4s0`.
3. `make check LIMIT=edge`, read the diff, then `make deploy LIMIT=edge`. It sets DNS, firewall and the AdGuard answers to the new address.

From the console, the same result is the stanza below in `/etc/network/interfaces.d/lan`, with `/etc/network/interfaces` reduced to the loopback and `source /etc/network/interfaces.d/*`, followed by a reboot:

```
allow-hotplug enp4s0
iface enp4s0 inet static
	address 192.168.7.10/24
	gateway 192.168.7.1
	dns-nameservers 192.168.7.1 1.1.1.1
iface enp4s0 inet6 auto
```

Checks on the edge:

- internet works and `chronyc tracking` shows a synchronised clock
- `docker ps` lists all stacks as up
- AdGuard answers on `192.168.7.10` and resolves the homelab names to `192.168.7.10`
- `systemctl start homelab-edge-restic.service` ends with a snapshot in the local and the offsite repository
- `wg show` lists the peers

Undo: the node reverts alone if it is not confirmed. Afterwards, the previous Git revision and a new converge.

## Step 3: switch

`SWITCH_HOST=<switch-link-local> make switch-check`, then `make switch`. The credentials come from `SWITCH_USER` and `SWITCH_PASS` in the environment.

From the console, the same result is:

```
config
interface vlan 1
 ip address 192.168.7.2 255.255.255.0
exit
no ip route 0.0.0.0/0 192.168.42.1
ip route 0.0.0.0/0 192.168.7.1
end
write
y
```

Check: `show ip route` lists the default route via `192.168.7.1`, a ping to `1.1.1.1` succeeds and the switch answers from the workstation.

Notes learnt on this firmware: SSH refuses `exec`, so scripts talk telnet through an interactive session. `config` enters configuration mode from `Switch#`. A `?` at the end of a line is executed. A wrong telnet login locks the console for two minutes. SSH allows one connection at a time.

## Step 4: DNS through the edge

Only after step 2 passes. In Freebox OS, the owner sets the DHCP DNS to `192.168.7.10` then `192.168.7.1`, and exports the configuration. A client keeps working through the Freebox if the edge goes down.

## Step 5: public access

In Freebox OS, the owner creates the forwards below and exports the configuration:

| Protocol | Port | Target |
| --- | --- | --- |
| TCP | 80 | `192.168.7.10` |
| TCP | 443 | `192.168.7.10` |
| UDP | 443 | `192.168.7.10` |
| UDP | 51820 | `192.168.7.10` |

Check from mobile data: `https://home.<domain>` answers and a WireGuard peer completes its handshake.

## What the owner provides

- The Freebox export after the manual setup, and the current IPv6 firewall setting (the box was reset, so its value is unknown). Exports stay outside git, since they hold the Wi-Fi password.
- The go before each step.

## After the migration

- [ ] WireGuard peers (`phone`, `omnibook`): `AllowedIPs = 192.168.7.0/24, 10.10.0.0/16`, `DNS = 192.168.7.10`
- [ ] Freebox: review remote API access, WAN ping reply and adblock
- [ ] Edge reboot to prove the configuration survives it
- [ ] Remove the old host keys for `10.0.0.10` and `192.168.42.x` from `~/.ssh/known_hosts`
- [ ] Tick the matching items in `network.md` (Open Items)
- [ ] Delete this file

## Kept for later

Package upgrades on the edge (Docker, kernel, libc), drifts found by the dry run (UDP buffer sysctls, the Docker apt key, and the AdGuard config that reports a change on every run and restarts the container), switch hardening and the Freebox static route for `10.10.0.0/16` each get their own window.
