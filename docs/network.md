# IP Address Plan

Overall Network: 10.0.0.0/8

Public IPv4: REDACTED-PUBLIC-IP

Public IPv6: 2a01:cb08:80dd:2300:2ef2:a5ff:fe1e:3d90 (/48)

---

## Active Subnets

### Core Infrastructure

Subnet: 10.0.0.0/16

Subnet Mask: 255.255.0.0

IP Range: 10.0.0.1 to 10.0.255.254

Allocations:

- 10.0.0.1 : Gateway
- 10.0.0.2 : Switch
- 10.0.0.3 : iLO

### Homelab

Subnet: 10.10.0.0/16

Subnet Mask: 255.255.0.0

IP Range: 10.10.0.1 to 10.10.255.254

Allocations:

- 10.10.10.10 : Baremetal host
- 10.10.1.0 : LXC
- 10.10.1.0 : VMs

### IoT

Subnet: 10.20.0.0/16

Subnet Mask: 255.255.0.0

IP Range: 10.20.0.1 to 10.20.255.254

Allocations:

- 10.20.1.10 : ShellyPlug 1
- 10.20.1.11 : ShellyPlug 2

### DHCP Pool

Subnet: 10.32.0.0/12

Subnet Mask: 255.240.0.0

IP Range: 10.32.0.1 to 10.47.255.254

## Software / configuration

For now everything done via livebox but this is limiting.

The goal is to have a adguard home doing DHCP/DNS

And for IPV6 blocking the livebox IPv6 RAs at a switch level to have more control with server RAs (custom DNS)

Wake on LAN needs to be done

---

<details>
  <summary>Obsolete Network </summary>

## Obsolete Network 

Local Subnet: 192.168.1.0/24

### Core Infrastructure & Management

IP Range: 192.168.1.0 to 192.168.1.20

Allocations:

- 192.168.1.1 : Gateway
- 192.168.1.7 : iLO

### DHCP Pool

IP Range: 192.168.1.11 to 192.168.1.99

### Reserved Homelab (Static)

IP Range: 192.168.1.100 to 192.168.1.199

Allocations:

- 192.168.1.100 : Baremetal IP
- ... : VMs / Containers / etc.

### Reserved Miscellaneous

IP Range: 192.168.1.200 to 192.168.1.255

Allocations:

- 192.168.1.251 : ShellyPlug 1
- 192.168.1.252 : ShellyPlug 2
- 192.168.1.254 : Switch

</details>
