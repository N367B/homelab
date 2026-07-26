# VPN and Remote Access

Status: plain WireGuard on the edge node.

## Decisions

| Decision            | Choice                                                |
| ------------------- | ----------------------------------------------------- |
| VPN                 | WireGuard                                             |
| Server              | `edge`                                                |
| Interface           | `wg0`                                                 |
| Listen port         | `51820/udp`                                           |
| VPN subnet          | `10.99.0.0/24`                                        |
| Edge VPN IP         | `10.99.0.1`                                           |
| Edge public key     | `zR64G3SFLAEN1OXATRbM1bOttgArlv3V+xGt9dVZeCI=`        |
| Client private keys | Generated and stored on each client, not in this repo |
| Client public keys  | Stored in Ansible variables                           |

## Addressing

The VPN subnet is `10.99.0.0/24`. It stays inside the global `10.0.0.0/8` homelab plan but outside the existing allocation ranges, so VPN traffic is easy to identify.

| Address                   | Purpose                     |
| ------------------------- | --------------------------- |
| `10.99.0.1`               | edge WireGuard endpoint     |
| `10.99.0.10-10.99.0.99`   | personal devices            |
| `10.99.0.100-10.99.0.199` | future service/device peers |
| `10.99.0.200-10.99.0.254` | reserved                    |

### Allocated peers

Authoritative list is `wireguard_peers` in `configure/group_vars/edge_nodes.yml`. Mirrored here so the next free address is obvious.

| Address      | Peer       | Device                  |
| ------------ | ---------- | ----------------------- |
| `10.99.0.11` | `phone`    | Phone                   |
| `10.99.0.12` | `omnibook` | Omnibook workstation    |

Next free: `10.99.0.13`.

## Peer Model

Peers are declared in `configure/group_vars/edge_nodes.yml` with public keys only:

```yaml
wireguard_peers:
  - name: <peer-name>
    address: <peer-address>/32
    public_key: <client-public-key>
    persistent_keepalive: 25
```

Client private keys are generated on the client itself and do not enter Git, SOPS, Ansible, or the edge node.

Current workflow:

1. Generate a WireGuard keypair on the client device.
2. Pick the next free address from the allocation table above.
3. Add only the client public key to `wireguard_peers` in `configure/group_vars/edge_nodes.yml`.
4. Run `make deploy LIMIT=edge`.
5. Import the client config into the WireGuard app, using **the same address** in the client's `[Interface] Address`.

> The client `Address` and the peer's `AllowedIPs` on the edge node must be the same `/32`. WireGuard drops every packet whose source address falls outside the peer's `AllowedIPs`, so a mismatch produces a healthy-looking handshake with zero usable traffic. `sudo wg show` on the edge node will report a recent handshake and a transfer counter stuck at a few hundred bytes.

This stays simple and Git-backed for now. A self-service peer UI can be added later if manual onboarding becomes annoying.

## Creating Client Keys

Linux/WSL:

```sh
wg genkey | tee client-private.key | wg pubkey > client-public.key
chmod 600 client-private.key
cat client-public.key
```

Windows with the official WireGuard app:

- Open WireGuard.
- Click `Add Tunnel`.
- Choose `Add empty tunnel`.
- The app generates the private/public keypair.
- Copy only the public key into `wireguard_peers`.
- Fill the rest of the tunnel config after the peer is deployed.

iOS/Android with the official WireGuard app:

- Add a new tunnel.
- Create from scratch.
- The app generates the private/public keypair.
- Copy only the public key into `wireguard_peers`.
- Fill the rest of the config or import a generated QR/config later.

## Client Config Shape

Split tunnel for homelab access:

`<peer-address>` is the address allocated to this device in the table above, and nowhere else.

```ini
[Interface]
PrivateKey = <client-private-key>
Address = <peer-address>/32
DNS = 10.0.0.10

[Peer]
PublicKey = zR64G3SFLAEN1OXATRbM1bOttgArlv3V+xGt9dVZeCI=
Endpoint = {{ homelab_domain }}:51820
AllowedIPs = 10.0.0.0/8
PersistentKeepalive = 25
```

This sends homelab traffic through VPN while normal internet traffic stays local. Full tunnel can be added later with `AllowedIPs = 0.0.0.0/0, ::/0` if needed.

Verification after connecting:

```sh
ping 10.99.0.1     # the tunnel itself
ping 10.0.0.10     # the LAN behind it, which needs forwarding + NAT to work
curl -I https://home.{{ homelab_domain }}
```

## Routing Peers Into the LAN

The tunnel only carries peers to `10.99.0.1`. Reaching the rest of the lab needs three things on the edge node, all owned by the `wireguard` role:

| Piece                             | Where                                                        |
| --------------------------------- | ------------------------------------------------------------ |
| `net.ipv4.ip_forward=1`           | `ansible.posix.sysctl` task                                   |
| Forward accept for `wg0` both ways | `wg-nat.nft.j2`, applied by `PostUp`                          |
| Masquerade `10.99.0.0/24` to LAN   | `wg-nat.nft.j2`, applied by `PostUp`                          |

Two details make this less obvious than it looks:

- Docker owns `table ip filter` and sets its FORWARD policy to `drop`. A drop policy wins over every other base chain on the hook, so the `accept` policy in our own `table inet homelab_filter` cannot rescue forwarded VPN packets. The accept rules therefore go in `DOCKER-USER`, the chain Docker documents as user-owned and jumps first from FORWARD.
- Docker also enables `ip_forward` on daemon start. That masks a missing sysctl until the day Docker is stopped, so it is declared explicitly rather than inherited.

Because the rules live in `PostUp`/`PostDown`, they exist exactly while the tunnel is up. `wg-quick@wg0` gets an `After=docker.service` drop-in so `DOCKER-USER` exists before `PostUp` runs at boot.

Peers are masqueraded, so LAN hosts see VPN traffic as coming from `10.0.0.10` and the Livebox needs no route back to `10.99.0.0/24`. The cost is that per-peer source addresses are not visible to LAN services. Revisit if a service ever needs to authorise by VPN source IP.

## Notes

- Livebox forwards `51820/udp` to `10.0.0.10` for external VPN access.
- AdGuard can be used as DNS over the tunnel via `10.0.0.10`.
- `AllowedIPs = 10.0.0.0/8` covers the whole LAN plan, which is also `10.0.0.0/8`. At home the tunnel therefore captures LAN traffic and sends it out to the public IP and back in through hairpin NAT. It works, but the sane move is to leave the tunnel down on the home network — AdGuard split-horizon already resolves service names to the internal ingress.
- Admin/internal services can later require VPN source ranges instead of broad LAN access.
