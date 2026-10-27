# Cooling (ML350 Gen9)

The compute node keeps its stock fans and heatsinks. Cooling is tuned through the modded iLO 4 firmware (v2.77, [ilo4_unlock](https://github.com/kendallgoto/ilo4_unlock)), which exposes the iLO fan controller over SSH. The Ansible role `ml350_fans` does the tuning.

## How it works

The iLO already runs a PID loop per sensor and drives the fans from the fastest one. Two things go wrong with the stock tuning on this machine.

- The CPU loops regulate the PECI margin to the throttle point (103 °C on the E5-2690 v4) with a setpoint of -6.00. The iLO lets the dies reach about 97 °C before it speeds the fans up. That is what happened when CPU 1 reached 96 °C in a stress test with the fans at 18-27 %.
- The iLO cannot see the GPU, the NVMe drives, the disks behind the LSI HBA or the X520 NIC. None of them report through OCSD.
- At idle the fans never go below about 19 %. The PCI zone loops have an output floor of 50/255, and the HD Max loop, blind behind the LSI HBA, falls back to an inlet curve that gives about 46/255.

The goal is the lowest noise that keeps every part safe. The fix has three layers. Each one keeps working when the layer above it is gone.

1. **iLO tuning.** The CPU loops (PIDs 1 and 2) get a setpoint of -20.00, which holds the dies at about 83 °C under full load. The fans stay at their minimum through moderate load. The regulation runs inside the iLO, so it keeps working when the host OS hangs, the agent dies or the network is down. Every stock loop stays active (DIMMs, VRs, chipset, PCI zones, exhaust) and the maximum speeds are never lowered.
2. **Agent on the compute node** (`ml350-fans-agent.service`). Every 10 s it reads coretemp, `nvidia-smi`, the NVMe composite temperature and SMART for the disks. It also pushes the quiet settings, which only make sense while it watches the disks. The output floor of the PCI zone loops goes from 50 to 16, so they still regulate but no longer hold a fixed floor, and the HD Max sensor is pinned at 30 °C so its fallback curve stays off. It sets a minimum fan speed (`fan p N min`) from the hottest part. Under normal load it requests nothing and the iLO alone drives the fans. A part that cannot be read requests a fallback floor instead of being ignored. That includes a single device among several, for example one disk out of six, or fewer devices found than the agent has seen since it started. It pushes again when the floor changes and every 5 minutes. A push gives up after 60 s.
3. **Last resort on the compute node.** When a part stays at its critical temperature for 2 minutes, the agent powers the host off cleanly with `systemctl poweroff`. This covers dead fans, or a hot host that cannot reach the iLO. The check runs before the iLO push, so a slow iLO cannot delay it, and the start time is kept in `/run` so an agent restart does not reset it.

The edge runs `ml350-fans apply` every 5 minutes from a systemd timer. It pushes the CPU setpoints over the LAN, so they come back after an iLO reset or a power cut even when the compute node is down or its network is not working. It leaves out the quiet settings, because without the agent nothing watches the disks.

## iLO behaviour to know

These were checked on this machine in October 2026.

- `fan` settings live in RAM only. An iLO reset (`reset /map1`) **and a host reboot** both put the stock tuning back, within seconds. Pushing them again therefore does not wear the flash, as far as can be seen from the outside. The old controller relied on `fan g nc` to avoid flash writes, but this firmware answers `fan: unsupported.` to it.
- The `fan` commands print their output only to the first SSH session opened after an iLO reset. Any TCP connection to port 22 counts, including a port probe. Other sessions get an empty answer, which is why the tool judges success by getting the prompt back and does not read state back. A prompt only shows the command was accepted. That the values take effect was checked by reading `fan info` from a first session, and by how the fans behave under load.
- One command per non-interactive `ssh ilo '<cmd>'` call. Chaining with `;` runs only the first one. The tool uses one interactive session per round.
- PID values use hundredths: `fan pid 1 sp -2000` means -20.00. `fan t N set` takes whole degrees, and sensor 7 (HD Max) adds its offset of 50, so `fan t 7 set -20` reads 30 °C. Setting 30 there reads 80 °C, a caution state that briefly raises the fans.
- Changing a setpoint makes the PID output jump for a few seconds (derivative kick). Sending the same value again does nothing.
- Each SSH session is short (about 3 s) and the agent and the edge open one every few minutes at most. The old controller opened one every 10 s with 24 commands, and the iLO stopped answering after a while.
- 4 fans are installed. PWM channels 0-3 drive fans 1-4, and 4-7 are the empty redundant bays. The CPU loops drive fans 2 and 3. The PCI zone loops drive fans 1 and 4, and under GPU load PID 56 (PCI zone 6, setpoint 37 °C) raises fan 1.

To read the full fan state (sensors, PID table, PWMs), reset the iLO, wait for it to answer ping, wait another minute without touching port 22, then open one SSH session and run `fan info`.

## Measurements

Inlet at 21-22 °C. Rows marked quiet use the lowered floors, measured after 30 minutes idle and 15 minutes of load. The other rows used the stock floors and a CPU setpoint of -28.00. The last row is the current setup.

| Load | CPU 1 | GPU | NVMe | Disks | DIMM | VR | Fans (PWM) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Idle | 30 °C | 26 °C | 34 °C | 40 °C | 27 °C | 33 °C | 47-50 |
| stress-ng 56 threads | 75 °C | | | | 28 °C | | 50-94 |
| GPU 168 W only | 50 °C | 76 °C (own fan 57 %) | | | | | 47-50 |
| CPU + RAM + GPU + disks, 10 min | 76 °C | 76 °C | | 41 °C | 35 °C | 64 °C | 56-94 |
| NVMe 2 GB/s writes, 5 min | | | 59 °C | | | | 47-50 |
| Idle, quiet settings | 38 °C | 25 °C | 38 °C | 43 °C | 26 °C | 36 °C | 16 on all fans |
| CPU + RAM + GPU + NVMe + disks, quiet, -28.00 | 76 °C | 75 °C | 63 °C | 44 °C | 36 °C | 67 °C | 57-98 / 16-19 on fan 4 |
| Same, quiet, -20.00 | 82-84 °C | 75 °C | 66 °C | 43 °C | 37 °C | 71 °C | 62-86 / 16-20 on fan 4 |

The GPU mostly cools itself. At 168 W it sits at 76 °C with the chassis fans at 19 %, and at about 70 °C with them at 63 %. Its own fan still has headroom. Its target is 83 °C and it slows down at 95 °C.

Failure tests run on the test OS, each one passed:

- Full combined load with compute to iLO traffic dropped by nftables for 5 minutes: CPU held at 74-77 °C by the iLO alone. The agent logged the failures and pushed again as soon as the iLO was reachable.
- `kill -9` of the agent: systemd restarted it within 5 s.
- Host reboot: the iLO went back to stock within 15 s, and the agent pushed the tuning again once it started, about 3.5 minutes later, during POST and boot when there is no load.
- iLO reset with the agent running: under full CPU load two minutes later, fan 2 regulated between 26 and 32 %, which matches the tuned loop. The stock loop would have stayed at 19 % until about 97 °C.
- Agent run with a lowered GPU curve during a GPU burn: the floor followed the GPU temperature from 74 to 160 on all four fans.
- iLO reset with the quiet settings: the fans went back to the stock 47-51, and the agent put every setting back as soon as it started.

## Thresholds

Defaults are in `configure/roles/ml350_fans/defaults/main.yml`. The curves start above the temperatures measured under full load, so the agent stays quiet in normal use.

| Part | Floor starts | Full speed | Power off after 2 min | Reference |
| --- | --- | --- | --- | --- |
| CPU (die) | 88 °C | 96 °C | 100 °C | throttle point 103 °C, held at about 83 °C by the iLO |
| GPU | 82 °C | 90 °C | 95 °C | target 83 °C, slowdown 95 °C, shutdown 98 °C |
| NVMe | 70 °C | 80 °C | 82 °C | warning 83-84 °C (Samsung PM9A1, WD SN750) |
| Disks | 46 °C | 55 °C | 60 °C | HGST He10 maximum operating 60 °C |

## Setup

The iLO account `fanctl` has no privileges. Its SSH key and password are in `secrets/ilo-fans.sops.yaml`. To recreate it after an iLO reset to factory defaults:

```sh
ssh ilo 'create /map1/accounts1 username=fanctl password=<from sops> name=fanctl'
# serve the public key over HTTP from a host the iLO can reach, then:
ssh ilo 'oemhp_loadSSHKey /map1/accounts1/fanctl -source http://<host>:<port>/fanctl.pub'
```

The public key comes from the private key in the SOPS file (`ssh-keygen -y -f <key>`). The iLO only accepts RSA keys here.

Deploy with `make deploy LIMIT=compute EXTRA="--tags fans"` (agent) and `make deploy LIMIT=edge EXTRA="--tags fans"` (apply timer).

## Operating

- State and decisions: `journalctl -u ml350-fans-agent` on the compute node. A line is logged each time the floor changes.
- Current readings and the floor the agent would request: `sudo ml350-fans status`.
- Push the tuning by hand, with an optional floor: `sudo ml350-fans apply --floor 120`. The agent takes over again at its next round.
- Go back to the stock iLO tuning: stop the agent and the edge timer, then `sudo ml350-fans restore`.

## Limits

- The LSI HBA (40 mm fan on the heatsink) and the X520 NIC have no readable temperature. They rely on the PCI zone loops of the iLO.
- If the iLO resets while both the edge and the compute agent are down, the stock tuning stays until one of them is back. The CPUs then run up to about 97 °C, which is still inside Intel limits, and throttle by themselves above that. With either one running, this lasts 5 minutes at most.
- If the agent dies while the host keeps working, the last floor and the quiet settings stay in place until the next host reboot or iLO reset. Nothing then watches the disks, the NVMe drives or the GPU. The iLO tuning still protects the CPUs and memory, and the iLO goes back to its louder stock floors at the next reset.
