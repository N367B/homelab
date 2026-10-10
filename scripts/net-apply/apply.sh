#!/usr/bin/env bash
# Move a node to the address its network role already wrote to disk, without
# locking it out.
#
#   apply.sh <ssh-target-now> <ssh-target-after> <interface>
#   apply.sh noe@192.168.42.10 noe@192.168.7.10 enp4s0
#
# 1. A timer is armed on the node. After 3 minutes it puts the previous address
#    and default route back, unless the node was confirmed from its new address.
# 2. The node reloads its interface from /etc/network/interfaces.d/lan.
# 3. This script connects to the new address and creates the confirmation file,
#    which cancels the revert.
#
# The workstation needs to reach the new address first (its own network configuration, see docs/network-migration.md).
set -euo pipefail
[ $# -eq 3 ] || { sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
now=$1; after=$2; iface=$3
key=${SSH_KEY:-$HOME/.ssh/homelab}
ssh_opts=(-i "$key" -o BatchMode=yes -o ConnectTimeout=6 -o StrictHostKeyChecking=accept-new)

echo "arming the revert on $now"
ssh "${ssh_opts[@]}" "$now" "IFACE=$iface bash -s" <<'REMOTE'
set -euo pipefail
old_addr=$(ip -4 -o addr show dev "$IFACE" scope global | awk '{print $4}' | head -n1)
old_gw=$(ip -4 route show default dev "$IFACE" | awk '{print $3}' | head -n1)
sudo rm -f /run/homelab-net-keep
sudo systemctl stop homelab-net-revert.timer homelab-net-revert.service 2>/dev/null || true
sudo systemd-run --quiet --unit=homelab-net-revert --on-active=180 /bin/sh -c "
  [ -e /run/homelab-net-keep ] && exit 0
  ip -4 addr flush dev $IFACE
  ip -4 route flush default dev $IFACE
  ip addr add $old_addr dev $IFACE
  ip route replace default via $old_gw dev $IFACE"
# The session ends when the address changes, so the reload runs detached.
sudo systemd-run --quiet --unit=homelab-net-apply --on-active=2 /bin/sh -c "
  ip -4 addr flush dev $IFACE
  ip -4 route flush default dev $IFACE
  ifup --force $IFACE"
echo "revert armed ($old_addr via $old_gw), reload scheduled"
REMOTE

echo "waiting for the node at $after"
for _ in $(seq 1 30); do
  if ssh "${ssh_opts[@]}" "$after" 'sudo touch /run/homelab-net-keep' 2>/dev/null; then
    echo "confirmed from $after, the revert is cancelled"
    exit 0
  fi
  sleep 3
done
echo "no answer from $after: the node reverts to its previous address on its own" >&2
exit 1
