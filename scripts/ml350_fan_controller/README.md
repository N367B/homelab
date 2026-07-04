# ML350 Gen9 Fan Controller

This script provides dynamic, software-defined thermal management for HPE ProLiant ML350 Gen9 servers running the modded iLO 4 firmware (v2.77+).

By default, the modded firmware completely disables the server's native automatic thermal ramping to give you manual control over the fans. However, static fan speeds are dangerous for dynamic workloads. This script acts as an intelligent daemon, monitoring all sensors via Linux and dynamically adjusting the fans in iLO to maintain a perfect balance between acoustics and thermals.

## Known Issues and Our Solutions

When building a software controller for the modded iLO 4 firmware, you will run into several severe hardware bottlenecks. This script solves all of them:

1. **The NAND Flash Wear Issue (The 60-Second Hang)**
   * **Issue:** By default, every `fan p` command sent to iLO writes its new value directly to the internal flash memory chip so it can persist across reboots. Because flash memory is slow, sending 24 commands (8 channels * 3 commands) takes almost a full minute to process. Doing this frequently burns through the flash chip's write-cycles and prematurely kills your iLO controller.
   * **Solution:** We prefix the command batch with `fan g nc` (No-Commit). This brilliant hardware flag forces iLO to execute all subsequent fan changes purely in RAM. Command execution time drops from 58 seconds down to **1.5 seconds**, and flash memory wear is completely eliminated.

2. **The iLO Command Queue Deadlock**
   * **Issue:** Because default commands take 60 seconds to run, running a fan script on a normal cron job (e.g., every 30 seconds) will spawn SSH connections faster than iLO can close them. This results in orphaned SSH processes, filling iLO's command queue until the entire RTOS locks up and requires a hard power cycle.
   * **Solution:** By utilizing the `nc` flag above, the SSH connection gracefully opens, applies 24 commands, and closes within ~1.5 seconds, ensuring the command queue stays perfectly clean even if polled every 10 seconds. 

3. **Premature SSH Timeouts**
   * **Issue:** Sometimes the internal iLO RTOS is busy (like during boot) and delays sending the `</>hpiLO->` prompt. Standard SSH client configurations with aggressive `ServerAliveInterval` values will kill the connection mid-execution, leaving orphaned tasks.
   * **Solution:** The script explicitly passes `ServerAliveInterval=15` and `ServerAliveCountMax=3` via SSH, giving the management chip plenty of buffer to respond.

4. **The "Missing HP-iLO Kernel Module" Conflict**
   * **Issue:** On the host OS, the `hpilo` kernel module attempts to constantly poll the CHIF interface, competing with the SSH daemon for access to the fan controller.
   * **Solution:** It is highly recommended to blacklist the `hpilo` module on the compute node OS to give the SSH interface exclusive, uninterrupted access to iLO.

## Key Features
* **Intelligent Curve Smoothing**: Implements a `DOWN_STEP` logic so that when the server cools, the fans gently ramp down rather than abruptly shutting off and causing thermal spikes.
* **Multi-Sensor Awareness**: Monitors the CPU, GPU (via `nvidia-smi`), NVMe, Aux/PCIe, and HDDs, dynamically adjusting the fans to the single highest requirement.
* **Failsafes**: Built-in logic defaults to a safe high RPM if sensors fail to read for a configured number of consecutive polling cycles.

## Prerequisites
* Linux OS running on the bare metal.
* `python3` and `python3-pexpect`
* `lm-sensors` and `smartmontools` (for disk temperatures)
* `nvidia-smi` (if a GPU is installed)
* Configured SSH access to the iLO 4 management interface (key-based auth highly recommended to avoid passing passwords).

## Installation

1. Install dependencies:
   ```bash
   sudo apt update
   sudo apt install python3-pexpect lm-sensors smartmontools
   ```

2. Copy `.env.example` to `.env` and fill in your iLO target and SSH credentials.

3. Setup a cronjob or Systemd timer to execute `ml350_fan.py` every 10-15 seconds. Note that since it must read disk and CPU sensors, it should typically be executed as `root` (or a user with permissions to read SMART data).

### Example Systemd Service
Create `/etc/systemd/system/fan-control.service`:
```ini
[Unit]
Description=ML350 Gen9 Fan Controller
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/ml350_fan_controller
ExecStart=/bin/bash -c "while true; do /usr/bin/python3 ml350_fan.py; sleep 10; done"
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fan-control.service
```

## Customizing Thermal Curves
The script includes predefined `CPU_CURVE`, `GPU_CURVE`, `NVME_CURVE`, `AUX_CURVE`, and `DISK_CURVE` tables.

Open `ml350_fan.py` to adjust them. They are defined as `(temperature_C, PWM_value)`.
* PWM ranges from `16` (6% fan speed, virtually silent) to `255` (100% fan speed, jet engine).
* 128 PWM = ~50% fan speed.

## Troubleshooting
* If the script hangs or times out, ensure the iLO SSH timeout settings in `.env` are sufficient. The script defaults to passing `ServerAliveInterval=15` to SSH to ensure it doesn't drop the connection during fast polling.
* If you need to manually restore the iLO to default cooling (or clear all overrides), run: `python3 ml350_fan.py --restore`.
