#!/usr/bin/env python3
"""Bring the switch management address, netmask and default route to the state in
configure/group_vars/switch.yml, then save the configuration.

  apply.py --check     print what differs, change nothing
  apply.py             change what differs and write the startup-config

The running and the startup configuration are both compared to the desired state.
Extra default routes are removed. The run succeeds only when the startup-config,
read back after `write`, matches.

The credentials are SWITCH_USER and SWITCH_PASS from the environment. The switch
is found at its desired address first, then at the addresses in SWITCH_HOST
(comma separated).

Firmware notes: SSH refuses `exec`, so this talks telnet through an interactive
session. A wrong login locks the console for two minutes, so there is exactly one
login attempt per run. A trailing `?` on a line is executed, never shown as help.
"""
import argparse
import os
import re
import socket
import sys
import time
from pathlib import Path

import yaml

STATE = Path(__file__).resolve().parents[2] / "configure/group_vars/switch.yml"


class Session:
    def __init__(self, host):
        self.sock = socket.create_connection((host, 23), timeout=6)
        self.sock.settimeout(2)

    def read(self, wait):
        time.sleep(wait)
        out = b""
        try:
            while chunk := self.sock.recv(4096):
                out += chunk
        except OSError:
            pass
        return re.sub(rb"\xff[\xfb-\xfe].", b"", out).decode(errors="ignore")

    def send(self, line, wait=1.5):
        self.sock.sendall(line.encode() + b"\r\n")
        return self.read(wait)

    def login(self, user, password):
        if "login" not in self.read(2).lower():
            sys.exit("no login prompt")
        if "assword" not in self.send(user):
            sys.exit("no password prompt")
        if "#" not in self.send(password, 2):
            sys.exit("login refused; stopping so the console does not lock")

    def close(self):
        try:
            self.send("exit", 0.5)
            self.sock.close()
        except OSError:
            pass


def reachable(host):
    try:
        socket.create_connection((host, 23), timeout=3).close()
        return True
    except OSError:
        return False


def netmask(prefix):
    bits = (0xFFFFFFFF << (32 - int(prefix))) & 0xFFFFFFFF
    return ".".join(str((bits >> shift) & 255) for shift in (24, 16, 8, 0))


def show(session, command):
    out = session.send(command, 3)
    for _ in range(40):
        if "--More--" not in out[-40:]:
            break
        out += session.send(" ", 1)
    return out.replace("\r", "")


def parse_config(text, name):
    addr = re.search(r"interface Vlan1\s+ip address (\d+\.\d+\.\d+\.\d+) (\d+\.\d+\.\d+\.\d+)", text, re.I)
    if not addr or "end" not in text:
        sys.exit(f"cannot read the {name} configuration; nothing was changed")
    return {
        "address": addr.group(1),
        "netmask": addr.group(2),
        "routes": sorted(re.findall(r"^ip route 0\.0\.0\.0/0 (\d+\.\d+\.\d+\.\d+)", text, re.M)),
    }


def read_state(session):
    show(session, "terminal length 0")
    return {
        "running": parse_config(show(session, "show running-config"), "running"),
        "startup": parse_config(show(session, "show startup-config"), "startup"),
    }


def differences(state, want):
    wanted = {"address": want["address"], "netmask": want["netmask"], "routes": [want["gateway"]]}
    found = []
    for which in ("running", "startup"):
        for key, value in wanted.items():
            if state[which][key] != value:
                found.append((f"{which} {key}", state[which][key], value))
    return found


def connect(candidates):
    user, password = os.environ["SWITCH_USER"], os.environ["SWITCH_PASS"]
    for host in candidates:
        if reachable(host):
            session = Session(host)
            session.login(user, password)
            return host, session
    sys.exit(f"switch not found at any of: {', '.join(candidates)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    want = yaml.safe_load(STATE.read_text())["switch"]
    extra = [h for h in os.environ.get("SWITCH_HOST", "").split(",") if h]
    host, session = connect([want["address"]] + extra)
    state = read_state(session)
    print(f"Switch answers at {host}")
    changes = differences(state, want)
    for key, old, new in changes:
        print(f"  {key}: {old} -> {new}")
    if not changes and state["running"] == state["startup"]:
        print("  nothing to change")
        session.close()
        return
    if args.check:
        session.close()
        return

    running = state["running"]
    if running["address"] != want["address"]:
        session.send("config")
        session.send("interface vlan 1")
        session.send(f"ip address {want['address']} {want['netmask']}", 1)
        session.close()
        for _ in range(20):
            time.sleep(3)
            if reachable(want["address"]):
                break
        else:
            sys.exit(f"switch not reachable at {want['address']}; reach that subnet from the workstation "
                     "(workstation network configuration) and run again")
        host, session = connect([want["address"]])
        state = read_state(session)
        running = state["running"]

    session.send("config")
    if running["netmask"] != want["netmask"]:
        session.send("interface vlan 1")
        session.send(f"ip address {want['address']} {want['netmask']}", 1)
        session.send("exit")
    for gateway in running["routes"]:
        if gateway != want["gateway"]:
            session.send(f"no ip route 0.0.0.0/0 {gateway}")
    if want["gateway"] not in running["routes"]:
        session.send(f"ip route 0.0.0.0/0 {want['gateway']}")
    session.send("end")
    session.send("write", 1.5)
    session.send("y", 4)
    final = read_state(session)
    session.close()
    left = differences(final, want)
    if left:
        print("Result: still differs:")
        for key, old, new in left:
            print(f"  {key}: {old} (wanted {new})")
        sys.exit(1)
    print("Result: running and startup configuration match the desired state")


if __name__ == "__main__":
    main()
