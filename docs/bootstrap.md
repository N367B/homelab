# Day 0: Manual Bootstrap Guide

This document outlines the strictly manual steps required to prepare the baremetal servers for Ansible automation. 

## Server 1 (HP ML350 Gen9)

### BIOS & iLO Prep

- Boot mode: UEFI
- Enable Wake-on-LAN (WoL) in BIOS.

### 2. OS Installation

- Insert USB
- Partitioning:
- Software Selection:

### Pre-Automation Setup

Once booted, log in as root directly via console:

1. `apt update && apt upgrade -y`
2. `apt install sudo git python3 -y`
3. Add user to sudoers: `usermod -aG sudo [username]`

### 4. SSH Key Injection

From the admin workstation (gaming PC), inject the SSH key:
`ssh-copy-id -i ~/.ssh/id_ed25519.pub [username]@10.10.10.10`

---

## Server 2 (AM06 Pro)

### 1. OS Installation

- Insert USB
- Partitioning:
- Software Selection:

### 2. Pre-Automation Setup

*(Repeat steps 3 and 4 from Server 1)*
