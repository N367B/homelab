# Information about hardware used and network details

## Hardware

## Server Infrastructure

### Server 1: HP ProLiant ML350 Gen9

- Role: Main Server (Shut down during the night)
- CPUs: 2 x Intel Xeon E5-2690 v4
- RAM: 256GB (8 x 32GB) DDR4 ECC at 2400MHz
  - max 2600MHz, but limited by CPU support
- Motherboard / Firmware: modded iLO 4 v2.77 (exposes the fan controller over SSH, see [cooling.md](cooling.md))
- GPU: ASUS Phoenix NVIDIA RTX 3060 (12GB)
- HBA: Inspur LSI 9300-8i 12Gbps PCIe HBA Controller (IT Mode)
- Networking: Intel X520 10G SFP+ (`ens3`, PCIe slot 3) on a DAC cable to the switch. No Wake-on-LAN support. The four onboard Broadcom 5719 ports are unused
- Cooling:
  - 1 x 92mm Noctua Fan (unused for now)
  - 1 x 40mm Noctua Fan (mounted directly on HBA)
- Power Supply: 800W PSU (Active) + 500W (Cold Spare)

Validation (test OS, October 2026). The node ran two full days of tests before its bootstrap. Raw logs are outside the repo.

- Reboots: 18 boots (warm, under load, cold off for 2 and 10 minutes, iLO hard power off, hard reset, iLO reset with the host up). Every boot saw 8 DIMMs and 252 GB, the GPU at PCIe Gen3 x16, the NIC at 10G and healthy pools. Power on to SSH takes 200-310 s. `incusd` was killed at start on one boot and came back by itself 10 minutes later.
- Load: four soak runs mixing CPU (stress-ng matrixprod on 56 threads), RAM, GPU (168 W) and fio with verification on both pools all passed, apart from the memory error below. Peaks with the quiet fan settings and 22-23 °C inlet were CPU 86 °C, GPU 80 °C, VR 73 °C, DIMM 47 °C, disks 47 °C, NVMe 67 °C, PSU 56 °C.
- Memory: memtester over 208 GB for 2 h 50 (1 h of it with 48 CPU threads loaded) and earlier 2 h 38 runs passed, with zero corrected errors all along. Bandwidth 45 GB/s.
- Storage: 600 GB written and verified on the RAIDZ2 pool (418 MB/s write, 781 MB/s read), 300 GB on the NVMe mirror (370 MB/s write, 3.8 GB/s read), scrubs clean, a 600 GB send/recv with matching checksums, and no ZFS damage after a hard power off and a hard reset under writes. Raw reads 2.9 and 3.2 GB/s per NVMe, 228-255 MB/s per disk.
- Network: zero link drops over two days with the new DAC cable. The first DAC dropped the link 94 times in one night. From the workstation to the node 7.3-9.2 Gbit/s, the other way 2.3-6.9 Gbit/s (WSL on the workstation suspected, not proven).

Memory history:

- 2026-10-26: POST error 207 on P2 DIMM 4, which was then disabled. The CPU 2 sticks were reseated, shuffled and cleaned, and all 8 have worked since.
- 2026-10-31: one uncorrectable memory error on P2 DIMM 9 (machine check, bank 7) after 2.5 minutes of full CPU load. ASR reset the node. Not reproduced in the hours of tests that followed. The two events hit different slots on CPU 2 and the sticks moved in between, so the stick, the slot and the CPU 2 memory controller are all possible. Follow-up in `todo.md`.

Storage Configuration (Server 1):

- HDD: 6 x 10TB HGST/WD Ultrastar SAS 12G, 4Kn (HUH721010AL42C0)
  - Health/Stats: 50k to 58k hours. SMART status Good, some corrected ECC, but 0 uncorrected, 0 non‑medium, 0 grown defects. Idle at 44-47 °C with the quiet fan settings
  - Modifications: PWDIS mitigation applied (Kapton tape on SATA power pins 1–3, unnecessary now)
- SATA SSDs: 2 x 240GB Samsung PM863A Sata III 2.5" (MZ-7LM240N)
  - Health/Stats: 56.7k and 61.7k hours. SMART 95% Good, no errors. Drive A: 54TB writes | Drive B: 3TB writes
- NVMe Storage:
  - 1 x 1TB WD BLACK SN750 NVMe (via NVMe to PCIe adapter), 17.5k hours, 3% used
  - 1 x 1TB Samsung PM9A1a NVMe (via NVMe to PCIe adapter), new
  - Both run at PCIe Gen3, the platform maximum

### Server 2: ACEMAGIC AM06 Pro

- Role: Critical services (DNS / OIDC / VPN / ingress / etc.)
- CPU: AMD Ryzen 7 7730U
- RAM: 32GB DDR4
- Storage: 512GB Samsung PM9A1 NVMe (with heatsink)
- Networking: 1 x 2.5G NIC + 1 x 1G NIC RJ45

### Cloud / Hosted Infrastructure

- PulseHeberg VPS: Nova G2
  - Hardware: 2 vCPU, 2GB RAM, 30GB SSD (RAID 10)
  - IPv4: `{{ vps_ipv4 }}`
  - IPv6: `{{ vps_ipv6 }}`
  - Reverse DNS (PTR): `{{ secondary_domain }}`
  - Capabilities: snapshots and arbitrary OS/software installs
  - Billing: 30.00 EUR annually
  - Renewal Date: 2027-05-22
  - Planned use: external uptime monitoring of the edge (e.g. Uptime Kuma), WireGuard rendezvous fallback when the home IP changes, secondary DNS candidate
- Infomaniak Web Hosting (Student)
  - Capabilities: Apache/PHP, MariaDB, Node.js, WordPress, and other managed web hosting options

### Power Backup (UPS)

- Model: HPE T1500 G5 INTL Tower UPS (brand new batteries)
- Capacity: 1550VA / 1100W
- Connectivity: Connected via USB to the Mini PC / Server (No NIC installed)
- Status: faulty (`AVR tempera. fault`, code `0x105`), not usable as a backup yet. See [ups.md](ups.md)

---

## Network Infrastructure & Smart Home

### Networking

- ISP & Speed: Free (Freebox Ultra) Symmetrical Fiber Optics (8 Gbps Down / 8 Gbps Up)
- 10G Switch (XikeStor SKS8300-8X), L2 only. The Freebox is the only router
- Client Connectivity: All primary devices have 10G NICs
- Hardware is generally budget Chinese networking gear, but runs reliably for now

### Smart Home & Automation

- Plugs/Relays: ShellyPlugs used for power management and monitoring

---

<details>
  <summary>Gaming Setup</summary>

## Workstation / Gaming Setup

### Core Components

- CPU: AMD Ryzen 7 7800X3D (4.2 GHz)
- Cooling: Arctic Liquid Freezer II 280 (280mm AIO)
- Motherboard: ASUS TUF GAMING X670E-PLUS
- GPU: Sapphire Radeon RX 7900 XTX PULSE
- RAM: 64GB (4 x 16GB) Corsair Vengeance DDR5 6000MHz CAS 30
  - 2 sticks support XMP/EXPO, 2 do not. Currently optimized at ~5600MHz (CL36-38-38-78), with room for further testing
- Power Supply: MSI MPG A850G PCIE5 (850W)
- Case: Fractal Design Pop XL Air
- NIC X520-DA1 SFP+

### Storage

- Primary/Fast: 2TB Crucial P3 Plus NVMe
- Secondary/Fast: 1TB Corsair MP600 CORE XT NVMe
- Bulk Storage: 4TB Seagate BarraCuda HDD

### Displays

- Primary: LG UltraGear 27G850A-B (27" 4K IPS, 240Hz)
- Secondary: Acer Nitro XV272U (27" WQHD IPS, 144Hz)

### Peripherals & Input

- Keyboard: Keychron V3 QMK (Keychron K Pro Blue switches) + Palm rest
- Mouse: Razer DeathAdder V2 X HyperSpeed
- Mousepad: SteelSeries Mousepad
- Controllers: Xbox One Controller + PC Adapter | Thrustmaster T.16000M FCS (Flight Stick)
- Webcam: UGREEN 4K Webcam

### Audio

- Speakers: Edifier R1280DBS (42W)
- Microphone: TONOR TC30
- Headphones/IEMs: 7Hz Salnotes Zero 2 IEM (plus other occasional pairs)

</details>

Additional cables, adapters, and unlisted accessories are present in the lab ecosystem.
