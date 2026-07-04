# ML350 Gen9 Fan Controller

This script provides software fan-floor control for HPE ProLiant ML350 Gen9 servers running the modded iLO 4 firmware v2.77 or newer.

The modded firmware exposes manual fan controls through iLO. Static fan speeds are risky on a machine with changing CPU, GPU, NVMe, and disk load, so this script reads host-side sensors and adjusts the iLO fan floor when needed.

## Known iLO behavior

The modded iLO 4 firmware has a few operational traps that matter if fan commands run often:

1. NAND flash writes

   By default, every `fan p` command sent to iLO writes the new value to internal flash so it can persist across reboots. Sending 24 commands, 8 channels times 3 commands, can take close to a minute and creates avoidable flash writes.

   The script prefixes each command batch with `fan g nc`, the no-commit mode. Fan changes are applied in RAM, command execution is much faster, and repeated polling does not write every change to flash.

2. iLO command queue

   If each run takes close to a minute, a short cron interval can open SSH sessions faster than iLO closes them. That can leave orphaned sessions and eventually wedge the management controller.

   With `fan g nc`, each run is short enough for frequent polling on this host. Keep the interval conservative if your iLO responds more slowly.

3. SSH timeouts

   During boot or heavy iLO activity, the `</>hpiLO->` prompt can be delayed. Aggressive SSH timeouts can kill the session mid-run.

   The script passes `ServerAliveInterval=15` and `ServerAliveCountMax=3` to SSH, and has a separate prompt timeout in `.env`.

4. `hpilo` kernel module conflict

   On the host OS, the `hpilo` kernel module can poll the CHIF interface while this script is controlling fans through SSH.

   If you see unstable iLO behavior, blacklist `hpilo` on the host so fan control happens through one path.

## Behavior

- `DOWN_STEP` limits how quickly the fan floor drops when temperatures fall.
- CPU, GPU through `nvidia-smi`, NVMe, aux or PCIe, and disk temperatures are read independently. The highest requested fan floor wins.
- After repeated CPU temperature read failures, the script uses the configured fallback PWM.

## Prerequisites

- Linux OS running on the bare metal.
- `python3` and `python3-pexpect`
- `lm-sensors` and `smartmontools` (for disk temperatures)
- `nvidia-smi` (if a GPU is installed)
- Configured SSH access to the iLO 4 management interface (key-based auth highly recommended to avoid passing passwords).

## Installation

1. Install dependencies:

   ```bash
   sudo apt update
   sudo apt install python3-pexpect lm-sensors smartmontools
   ```

2. Copy `.env.example` to `.env` and fill in your iLO target and SSH credentials.

3. Set up a systemd service, timer, or cron job to run `ml350_fan.py` every 10 to 15 seconds. Since it reads disk and CPU sensors, it should usually run as `root` or as a user with permission to read SMART data.

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

- PWM ranges from `16`, about 6 percent fan speed, to `255`, 100 percent fan speed.
- `128` PWM is about 50 percent fan speed.

## Troubleshooting

- If the script hangs or times out, make sure the iLO SSH timeout settings in `.env` are sufficient. The script passes `ServerAliveInterval=15` to SSH by default.
- If you need to manually restore the iLO to default cooling (or clear all overrides), run: `python3 ml350_fan.py --restore`.
