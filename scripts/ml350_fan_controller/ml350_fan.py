#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import pexpect
except ImportError:
    print(
        "Missing dependency: python3-pexpect\n"
        "Install it with: sudo apt install python3-pexpect",
        file=sys.stderr,
    )
    sys.exit(2)

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_FILE = SCRIPT_DIR / ".env"
STATE_FILE = SCRIPT_DIR / "ml350_fan.state.json"

ILO_PROMPT = r"</>hpiLO->"

CPU_CURVE = [
    (45.0, 16),
    (55.0, 24),
    (65.0, 32),
    (70.0, 50),
    (75.0, 70),
    (80.0, 90),
    (85.0, 128),
    (90.0, 168),
    (999.0, 240),
]

GPU_CURVE = [
    (55.0, 16),
    (65.0, 24),
    (75.0, 32),
    (80.0, 50),
    (84.0, 70),
    (88.0, 110),
    (999.0, 168),
]

NVME_CURVE = [
    (50.0, 16),
    (60.0, 24),
    (65.0, 32),
    (70.0, 50),
    (75.0, 70),
    (80.0, 90),
    (999.0, 128),
]

AUX_CURVE = [
    (60.0, 16),
    (65.0, 24),
    (70.0, 32),
    (75.0, 50),
    (80.0, 70),
    (85.0, 90),
    (999.0, 128),
]

DISK_CURVE = [
    (55.0, 16),
    (58.0, 24),
    (60.0, 32),
    (63.0, 50),
    (65.0, 70),
    (999.0, 128),
]


def log(msg: str) -> None:
    print(msg, flush=True)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list_int(name: str, default: list[int]) -> list[int]:
    value = os.environ.get(name)
    if not value:
        return default

    result = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            pass

    return result or default


def cfg() -> dict:
    load_env_file(ENV_FILE)

    return {
        "ilo_target": os.environ.get("ILO_TARGET", "ilo"),
        "ilo_password": os.environ.get("ILO_PASSWORD", ""),
        "ilo_ssh_options": os.environ.get("ILO_SSH_OPTIONS", ""),
        "channels": env_list_int("CHANNELS", list(range(8))),
        "ssh_connect_timeout": env_int("SSH_CONNECT_TIMEOUT", 5),
        "ilo_prompt_timeout": env_int("ILO_PROMPT_TIMEOUT", 10),
        "smart_poll_seconds": env_int("SMART_POLL_SECONDS", 120),
        "safe_fallback_pwm": env_int("SAFE_FALLBACK_PWM", 128),
        "temp_failure_safe_after": env_int("TEMP_FAILURE_SAFE_AFTER", 3),
        "down_step": env_int("DOWN_STEP", 16),
        "min_change": env_int("MIN_CHANGE", 8),
        "log_every_run": env_bool("LOG_EVERY_RUN", False),
        "always_start_controller": env_bool("ALWAYS_START_CONTROLLER", False),
        "retry_with_fan_g_start": env_bool("RETRY_WITH_FAN_G_START", True),
    }


def default_state() -> dict:
    return {
        "last_pwm": None,
        "temp_failures": 0,
        "last_disk_poll_ts": 0.0,
        "disk_temps": [],
        "last_summary": {},
    }


def load_state() -> dict:
    if not STATE_FILE.exists():
        return default_state()

    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return default_state()


def save_state(state: dict) -> None:
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    tmp.replace(STATE_FILE)


def clamp_pwm(value: int) -> int:
    return max(16, min(255, int(value)))


def valid_temp(value, low: float = 0.0, high: float = 120.0) -> bool:
    if not isinstance(value, (int, float)):
        return False
    return low <= float(value) <= high


def fmt_temp(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}C"

def fmt_pwm(value: int | None) -> str:
    if value is None:
        return "n/a"
    pwm = int(value)
    pct = round(pwm * 100 / 255)
    return f"{pwm} PWM (~{pct}% fan)"

def run_text(cmd: list[str], timeout: int = 10) -> str:
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        stdout = proc.stdout.strip()
        raise RuntimeError(stderr or stdout or "command failed")
    return proc.stdout


def run_json(cmd: list[str], timeout: int = 10) -> dict:
    return json.loads(run_text(cmd, timeout=timeout))


def collect_temp_inputs(node, temps: list[float]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key.endswith("_input") and valid_temp(value):
                temps.append(float(value))
            else:
                collect_temp_inputs(value, temps)
    elif isinstance(node, list):
        for item in node:
            collect_temp_inputs(item, temps)


def max_or_none(values: list[float]) -> float | None:
    return max(values) if values else None


def get_gpu_temp() -> float | None:
    if shutil.which("nvidia-smi") is None:
        return None

    try:
        out = run_text(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            timeout=5,
        )
    except Exception:
        return None

    temps = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            temp = float(line)
        except ValueError:
            continue
        if valid_temp(temp):
            temps.append(temp)

    return max_or_none(temps)


def get_sensor_readings() -> dict:
    data = run_json(["sensors", "-j"], timeout=5)

    cpu_packages: list[float] = []
    nvme_temps: list[float] = []
    aux_temps: list[float] = []

    for chip_name, chip_data in data.items():
        if not isinstance(chip_data, dict):
            continue

        if chip_name.startswith("power_meter-"):
            continue

        if chip_name.startswith("coretemp-"):
            for feature_name, feature_data in chip_data.items():
                if not isinstance(feature_data, dict):
                    continue
                if not feature_name.startswith("Package id "):
                    continue
                temp = feature_data.get("temp1_input")
                if valid_temp(temp):
                    cpu_packages.append(float(temp))
            continue

        chip_temps: list[float] = []
        collect_temp_inputs(chip_data, chip_temps)

        if chip_name.startswith("nvme-"):
            nvme_temps.extend(chip_temps)
        else:
            aux_temps.extend(chip_temps)

    return {
        "cpu_temp": max_or_none(cpu_packages),
        "gpu_temp": get_gpu_temp(),
        "nvme_temp": max_or_none(nvme_temps),
        "aux_temp": max_or_none(aux_temps),
    }


def scan_smart_devices() -> list[list[str]]:
    if shutil.which("smartctl") is None:
        return []

    try:
        out = run_text(["smartctl", "--scan"], timeout=5)
    except Exception:
        return []

    devices = []
    for raw_line in out.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        parts = shlex.split(line)
        if not parts:
            continue

        device = parts[0]
        if device.startswith("/dev/nvme"):
            continue

        devices.append(parts)

    return devices


def extract_smart_temp(data: dict) -> float | None:
    temp = data.get("temperature")
    if isinstance(temp, dict):
        current = temp.get("current")
        if valid_temp(current, low=1.0):
            return float(current)

    scsi_temp = data.get("scsi_temperature")
    if isinstance(scsi_temp, dict):
        current = scsi_temp.get("current")
        if valid_temp(current, low=1.0):
            return float(current)

    ata = data.get("ata_smart_attributes")
    if isinstance(ata, dict):
        table = ata.get("table")
        if isinstance(table, list):
            for row in table:
                if not isinstance(row, dict):
                    continue
                attr_id = row.get("id")
                if attr_id not in {190, 194}:
                    continue
                raw = row.get("raw")
                if not isinstance(raw, dict):
                    continue
                value = raw.get("value")
                if valid_temp(value, low=1.0):
                    return float(value)

    return None


def poll_disk_temps(state: dict, cfg_data: dict) -> tuple[list[float], str]:
    now = time.time()
    cached = state.get("disk_temps", [])

    if (
        now - float(state.get("last_disk_poll_ts", 0.0))
        < cfg_data["smart_poll_seconds"]
    ):
        return cached, "cached"

    devices = scan_smart_devices()
    if not devices:
        return cached, "none"

    temps: list[float] = []

    for parts in devices:
        device = parts[0]
        args = parts[1:]

        cmd = ["smartctl", "-j", "-a", *args, device]
        try:
            data = run_json(cmd, timeout=8)
        except Exception:
            continue

        temp = extract_smart_temp(data)
        if valid_temp(temp):
            temps.append(float(temp))

    if temps:
        state["disk_temps"] = temps
        state["last_disk_poll_ts"] = now
        return temps, "fresh"

    return cached, "cached" if cached else "none"


def pwm_for_temp(temp: float | None, curve: list[tuple[float, int]]) -> int:
    if temp is None:
        return 16

    for threshold, pwm in curve:
        if temp < threshold:
            return pwm

    return curve[-1][1]


def compute_desired_pwm(temps: dict) -> tuple[int, dict]:
    floors = {
        "cpu": pwm_for_temp(temps.get("cpu_temp"), CPU_CURVE),
        "gpu": pwm_for_temp(temps.get("gpu_temp"), GPU_CURVE),
        "nvme": pwm_for_temp(temps.get("nvme_temp"), NVME_CURVE),
        "aux": pwm_for_temp(temps.get("aux_temp"), AUX_CURVE),
        "disk": pwm_for_temp(temps.get("disk_temp"), DISK_CURVE),
    }

    desired = max(floors.values())

    cpu_temp = temps.get("cpu_temp")
    gpu_temp = temps.get("gpu_temp")
    nvme_temp = temps.get("nvme_temp")
    aux_temp = temps.get("aux_temp")
    disk_temp = temps.get("disk_temp")

    if cpu_temp is not None and cpu_temp >= 90.0:
        desired = max(desired, 255)
    elif cpu_temp is not None and cpu_temp >= 85.0:
        desired = max(desired, 220)

    if gpu_temp is not None and gpu_temp >= 88.0:
        desired = max(desired, 220)

    if nvme_temp is not None and nvme_temp >= 75.0:
        desired = max(desired, 220)

    if aux_temp is not None and aux_temp >= 85.0:
        desired = max(desired, 220)

    if disk_temp is not None and disk_temp >= 55.0:
        desired = max(desired, 220)

    return clamp_pwm(desired), floors


def choose_applied_pwm(
    desired_pwm: int,
    last_pwm: int | None,
    down_step: int,
    min_change: int,
) -> int:
    desired_pwm = clamp_pwm(desired_pwm)

    if last_pwm is None:
        return desired_pwm

    last_pwm = clamp_pwm(last_pwm)

    if desired_pwm > last_pwm:
        candidate = desired_pwm
    elif desired_pwm < last_pwm:
        candidate = max(desired_pwm, last_pwm - max(1, down_step))
    else:
        candidate = last_pwm

    if candidate != last_pwm and abs(candidate - last_pwm) < max(1, min_change):
        return last_pwm

    return clamp_pwm(candidate)


def build_ssh_command(cfg_data: dict) -> list[str]:
    ssh_bin = shutil.which("ssh")
    if ssh_bin is None:
        raise RuntimeError("ssh binary not found")

    cmd = [ssh_bin, "-tt"]
    cmd.extend(
        [
            "-o",
            f"ConnectTimeout={cfg_data['ssh_connect_timeout']}",
            "-o",
            "ServerAliveInterval=15",
            "-o",
            "ServerAliveCountMax=3",
        ]
    )

    extra = cfg_data.get("ilo_ssh_options", "").strip()
    if extra:
        cmd.extend(shlex.split(extra))

    cmd.append(cfg_data["ilo_target"])
    return cmd


def wait_for_prompt(child, cfg_data: dict) -> str:
    while True:
        idx = child.expect(
            [
                ILO_PROMPT,
                r"(?i)password:",
                r"(?i)are you sure you want to continue connecting",
                r"(?i)permission denied",
                pexpect.EOF,
                pexpect.TIMEOUT,
            ],
            timeout=cfg_data["ilo_prompt_timeout"],
        )

        if idx == 0:
            return child.before or ""

        if idx == 1:
            password = cfg_data.get("ilo_password", "")
            if not password:
                raise RuntimeError(
                    "SSH password prompt received, but ILO_PASSWORD is empty"
                )
            child.sendline(password)
            continue

        if idx == 2:
            child.sendline("yes")
            continue

        if idx == 3:
            raise RuntimeError("SSH authentication failed: permission denied")

        if idx == 4:
            raise RuntimeError(f"SSH session ended early: {child.before or ''}")

        raise RuntimeError("Timed out waiting for iLO prompt")


def run_ilo_commands(
    cfg_data: dict,
    commands: list[str],
    include_start: bool = False,
) -> list[tuple[str, str]]:
    final_commands = ["fan g nc"]
    if include_start:
        final_commands.append("fan g start")
    final_commands.extend(commands)

    cmd = build_ssh_command(cfg_data)
    child = pexpect.spawn(
        cmd[0],
        cmd[1:],
        encoding="utf-8",
        timeout=cfg_data["ilo_prompt_timeout"],
    )
    child.delaybeforesend = 0.05

    outputs: list[tuple[str, str]] = []

    try:
        wait_for_prompt(child, cfg_data)

        for command in final_commands:
            child.sendline(command)
            output = wait_for_prompt(child, cfg_data)
            outputs.append((command, output.strip()))

        child.sendline("exit")
        try:
            child.expect(pexpect.EOF, timeout=2)
        except Exception:
            pass

        return outputs
    finally:
        if child.isalive():
            child.close(force=True)


def build_apply_commands(channels: list[int], pwm: int) -> list[str]:
    commands = []
    for channel in channels:
        commands.append(f"fan p {channel} unlock")
        commands.append(f"fan p {channel} max 255")
        commands.append(f"fan p {channel} min {pwm}")
    return commands


def build_restore_commands(channels: list[int]) -> list[str]:
    return build_apply_commands(channels, 16)


def summary_text(
    temps: dict,
    floors: dict,
    desired_pwm: int | None,
    applied_pwm: int | None,
    state: dict,
    disk_source: str,
) -> str:
    return (
        "temps(cpu={cpu}, gpu={gpu}, nvme={nvme}, aux={aux}, disk={disk}) "
        "floors(cpu={cpu_floor}, gpu={gpu_floor}, nvme={nvme_floor}, "
        "aux={aux_floor}, disk={disk_floor}) "
        "decision(desired={desired}, applied={applied}, last={last}) "
        "disk_source={disk_source}"
    ).format(
        cpu=fmt_temp(temps.get("cpu_temp")),
        gpu=fmt_temp(temps.get("gpu_temp")),
        nvme=fmt_temp(temps.get("nvme_temp")),
        aux=fmt_temp(temps.get("aux_temp")),
        disk=fmt_temp(temps.get("disk_temp")),
        cpu_floor=fmt_pwm(floors.get("cpu")),
        gpu_floor=fmt_pwm(floors.get("gpu")),
        nvme_floor=fmt_pwm(floors.get("nvme")),
        aux_floor=fmt_pwm(floors.get("aux")),
        disk_floor=fmt_pwm(floors.get("disk")),
        desired=fmt_pwm(desired_pwm),
        applied=fmt_pwm(applied_pwm),
        last=fmt_pwm(state.get("last_pwm")),
        disk_source=disk_source,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ML350 Gen9 fan floor controller for modded iLO4"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and log the action, but do not touch iLO",
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Unlock all channels and reset min=16 max=255",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show temp inputs and chosen PWM without changing iLO",
    )

    args = parser.parse_args()

    cfg_data = cfg()
    state = load_state()

    if args.restore:
        commands = build_restore_commands(cfg_data["channels"])
        if args.dry_run or args.status:
            log(
                "[restore] dry-run channels={} commands={}".format(
                    cfg_data["channels"], len(commands)
                )
            )
            return 0

        try:
            run_ilo_commands(cfg_data, commands, include_start=True)
        except Exception as exc:
            log(f"[restore] failed: {exc}")
            return 1

        state["last_pwm"] = 16
        state["temp_failures"] = 0
        state["last_summary"] = {"mode": "restore", "ts": time.time()}
        save_state(state)
        log(f"[restore] restored channels {cfg_data['channels']} to min=16 max=255")
        return 0

    try:
        temps = get_sensor_readings()
    except Exception as exc:
        temps = {
            "cpu_temp": None,
            "gpu_temp": None,
            "nvme_temp": None,
            "aux_temp": None,
        }
        log(f"[warn] failed to read sensors: {exc}")

    disk_temps, disk_source = poll_disk_temps(state, cfg_data)
    temps["disk_temp"] = max_or_none(disk_temps)

    floors = {
        "cpu": 16,
        "gpu": 16,
        "nvme": 16,
        "aux": 16,
        "disk": 16,
    }

    desired_pwm: int | None
    cpu_temp = temps.get("cpu_temp")

    if cpu_temp is None:
        state["temp_failures"] = int(state.get("temp_failures", 0)) + 1

        if (
            cfg_data["temp_failure_safe_after"] > 0
            and state["temp_failures"] >= cfg_data["temp_failure_safe_after"]
        ):
            desired_pwm = cfg_data["safe_fallback_pwm"]
            log(
                "[warn] CPU temp missing for {} consecutive runs; "
                "using safe fallback PWM {}".format(
                    state["temp_failures"], desired_pwm
                )
            )
        else:
            desired_pwm = state.get("last_pwm")
            log(
                "[warn] CPU temp missing; keeping current floor "
                f"(failure count={state['temp_failures']})"
            )
    else:
        state["temp_failures"] = 0
        desired_pwm, floors = compute_desired_pwm(temps)

    applied_pwm = choose_applied_pwm(
        desired_pwm if desired_pwm is not None else 16,
        state.get("last_pwm"),
        cfg_data["down_step"],
        cfg_data["min_change"],
    )

    summary = summary_text(
        temps=temps,
        floors=floors,
        desired_pwm=desired_pwm,
        applied_pwm=applied_pwm,
        state=state,
        disk_source=disk_source,
    )

    if args.status:
        log(summary)
        return 0

    if desired_pwm is None:
        if cfg_data["log_every_run"]:
            log(f"[hold] {summary}")
        state["last_summary"] = {"summary": summary, "ts": time.time()}
        save_state(state)
        return 0

    last_pwm = state.get("last_pwm")
    changed = last_pwm != applied_pwm

    if args.dry_run:
        prefix = "[dry-run]"
        if changed:
            log(f"{prefix} would apply {fmt_pwm(applied_pwm)}; {summary}")
        else:
            log(f"{prefix} no change; {summary}")
        return 0
    if not changed:
        if cfg_data["log_every_run"]:
            log(f"[noop] {summary}")
        state["last_summary"] = {"summary": summary, "ts": time.time()}
        save_state(state)
        return 0

    commands = build_apply_commands(cfg_data["channels"], applied_pwm)

    include_start = cfg_data["always_start_controller"]

    try:
        run_ilo_commands(
            cfg_data,
            commands,
            include_start=include_start,
        )
    except Exception as exc:
        if cfg_data["retry_with_fan_g_start"] and not include_start:
            log(f"[warn] apply failed once, retrying with fan g start: {exc}")
            try:
                run_ilo_commands(
                    cfg_data,
                    commands,
                    include_start=True,
                )
            except Exception as retry_exc:
                log(f"[error] apply failed after retry: {retry_exc}")
                return 1
        else:
            log(f"[error] apply failed: {exc}")
            return 1

    state["last_pwm"] = applied_pwm
    state["last_summary"] = {"summary": summary, "ts": time.time()}
    save_state(state)

    log(
        f"[apply] apply={fmt_pwm(applied_pwm)} "
        f"channels={cfg_data['channels']} {summary}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
