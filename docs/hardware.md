# Information about hardware used and network details

## Hardware

## Server Infrastructure

### Server 1: HP ProLiant ML350 Gen9

- Role: Main Server (Shut down during the night)
- CPUs: 2 x Intel Xeon E5-2690 v4
- RAM: 256GB (8 x 32GB) DDR4 ECC at 2400MHz
  - max 2600MHz, but limited by CPU support
- Motherboard / Firmware: Latest modded iLO/firmware applied (enables fan control, but seems broken)
- GPU: ASUS Phoenix NVIDIA RTX 3060 (12GB)
- HBA: Inspur LSI 9300-8i 12Gbps PCIe HBA Controller (IT Mode)
- Networking: 10G NIC SFP+
- Cooling:
  - 1 x 92mm Noctua Fan (unused for now)
  - 1 x 40mm Noctua Fan (mounted directly on HBA)
- Power Supply: 800W PSU (Active) + 500W (Cold Spare)

Storage Configuration (Server 1):
- HDD: 6 x 10TB HGST/WD Ultrastar SAS 12G, 4Kn (HUH721010AL42C0)
  - Health/Stats: 50k to 65k hours SMART status Good Some corrected ECC, but 0 uncorrected, 0 non‑medium, 0 grown defects
  - Modifications: PWDIS mitigation applied (Kapton tape on SATA power pins 1–3, unnecessary now)
- SATA SSDs: 2 x 240GB Samsung PM863A Sata III 2.5" (MZ-7LM240N)
  - Health/Stats: ~56k hours SMART 95% Good, no errors Drive A: 54TB writes | Drive B: 3TB writes
- NVMe Storage:
  - 1 x 1TB WD BLACK SN750 NVMe (via NVMe to PCIe adapter)
  - 1 x 1TB Samsung PM9A1a NVMe (via NVMe to PCIe adapter)

### Server 2: ACEMAGIC AM06 Pro

- Role: Critical services (DHCP / DNS / IPv6 RA / OIDC / VPN / etc.)
- CPU: AMD Ryzen 7 7730U
- RAM: 32GB DDR4
- Storage: 512GB SSD SATA (to be upgraded to NVMe with 512GB Samsung PM9A1)
- Networking: 1 x 2.5G NIC + 1 x 1G NIC RJ45

### Power Backup (UPS)

- Model: HPE T1500 G5 INTL Tower UPS (brand new batteries)
- Capacity: 1550VA / 1100W
- Connectivity: Connected via USB to the Mini PC / Server (No NIC installed)

---

## Network Infrastructure & Smart Home

### Networking

- ISP & Speed: Orange Symmetrical Fiber Optics (8 Gbps Down / 8 Gbps Up)
- 10G Switch (XikeStor SKS8300-8X) routing 
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
  - 2 sticks support XMP/EXPO, 2 do not Currently optimized at ~5600MHz (CL36-38-38-78) Room for further optimization/testing
- Power Supply: MSI MPG A850G PCIE5 (850W)
- Case: Fractal Design Pop XL Air

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

>>> Additional cables, adapters, and various unlisted accessories are present in the lab ecosystem

</details>