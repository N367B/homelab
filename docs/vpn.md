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

## Peer Model

Peers are declared in `configure/group_vars/edge_nodes.yml` with public keys only:

```yaml
wireguard_peers:
  - name: phone
    address: 10.99.0.10/32
    public_key: <client-public-key>
    persistent_keepalive: 25
```

Client private keys are generated on the client itself and do not enter Git, SOPS, Ansible, or the edge node.

Current workflow:

1. Generate a WireGuard keypair on the client device.
2. Add only the client public key to `wireguard_peers` in `configure/group_vars/edge_nodes.yml`.
3. Run `make deploy LIMIT=edge`.
4. Import the client config into the WireGuard app.

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

```ini
[Interface]
PrivateKey = <client-private-key>
Address = 10.99.0.10/32
DNS = 10.0.0.10

[Peer]
PublicKey = zR64G3SFLAEN1OXATRbM1bOttgArlv3V+xGt9dVZeCI=
Endpoint = {{ homelab_domain }}:51820
AllowedIPs = 10.0.0.0/8
PersistentKeepalive = 25
```

This sends homelab traffic through VPN while normal internet traffic stays local. Full tunnel can be added later with `AllowedIPs = 0.0.0.0/0, ::/0` if needed.

Per-device example after adding this peer in Ansible:

```yaml
wireguard_peers:
  - name: bodin-laptop
    address: 10.99.0.10/32
    public_key: <laptop-public-key>
    persistent_keepalive: 25
```

Client config for that device:

```ini
[Interface]
PrivateKey = <laptop-private-key>
Address = 10.99.0.10/32
DNS = 10.0.0.10

[Peer]
PublicKey = zR64G3SFLAEN1OXATRbM1bOttgArlv3V+xGt9dVZeCI=
Endpoint = {{ homelab_domain }}:51820
AllowedIPs = 10.0.0.0/8
PersistentKeepalive = 25
```

Verification after connecting:

```sh
ping 10.99.0.1
ping 10.0.0.10
curl -I https://home.{{ homelab_domain }}
```

## Notes

- Livebox forwards `51820/udp` to `10.0.0.10` for external VPN access.
- AdGuard can be used as DNS over the tunnel via `10.0.0.10`.
- Admin/internal services can later require VPN source ranges instead of broad LAN access.
