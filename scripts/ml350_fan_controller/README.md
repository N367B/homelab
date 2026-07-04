# ML350 Gen9 Fan Controller

This script provides dynamic, software-defined thermal management for HPE ProLiant ML350 Gen9 servers running the modded iLO 4 firmware (v2.77+).

By default, the modded firmware completely disables the server's native automatic thermal ramping to give you manual control over the fans. However, static fan speeds are dangerous for dynamic workloads. This script acts as an intelligent daemon, monitoring all sensors via Linux and dynamically adjusting the fans in iLO to maintain a perfect balance between acoustics and thermals.

## Key Features
* **NAND Flash Bypass Trick (`fan g nc`)**: Safely executes all fan changes exclusively in iLO's RAM. This prevents the ~60-second command hanging issue, permanently eliminates the risk of command-queue lockups, and prevents wearing out the iLO NAND flash chip.
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
