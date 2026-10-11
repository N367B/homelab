#!/usr/bin/env bash
# Move a node to the address its network role already wrote to disk, without
# locking it out.
#
#   apply.sh <ssh-target-now> <ssh-target-after> <interface>
#   apply.sh noe@<old-address> noe@192.168.7.10 enp4s0
#
# 1. A timer is armed on the node. After 3 minutes it puts the previous address
#    and default route back, in the kernel and in /etc/network/interfaces.d/lan,
#    unless the node was confirmed.
# 2. The node reloads its interface from /etc/network/interfaces.d/lan.
# 3. This script connects to the target and waits for the reload to finish. It
#    checks the address, the default route and a ping outside the subnet
#    (CHECK_HOST, default 1.1.1.1) against the values frozen when the revert was
#    armed, then creates the confirmation file, which cancels the revert. The
#    confirmation and the revert take the same lock, so only one of them decides:
#    once the revert has run, no confirmation is accepted.
#
# The revert covers one global IPv4 address and one default route, which is what
# the edge has. It rebuilds interfaces.d/lan from the previous address, the
# previous gateway and the DNS line of the current file; it does not restore a
# copy of the old file. It does not survive a reboot during the 3 minutes: the
# files on disk are the new ones until the timer fires.
#
# The workstation needs to reach the new address first (see docs/network-migration.md).
set -euo pipefail
[ $# -eq 3 ] || { sed -n '2,27p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
now=$1; after=$2; iface=$3
key=${SSH_KEY:-$HOME/.ssh/homelab}
check_host=${CHECK_HOST:-1.1.1.1}
ssh_opts=(-i "$key" -o BatchMode=yes -o ConnectTimeout=6 -o StrictHostKeyChecking=accept-new)

echo "arming the revert on $now"
ssh "${ssh_opts[@]}" "$now" "IFACE=$iface bash -s" <<'REMOTE'
set -euo pipefail
old_addr=$(ip -4 -o addr show dev "$IFACE" scope global | awk '{print $4}' | head -n1)
old_gw=$(ip -4 route show default dev "$IFACE" | awk '{print $3}' | head -n1)
[ -n "$old_addr" ] && [ -n "$old_gw" ] || { echo "no global IPv4 address or default route on $IFACE" >&2; exit 1; }
sudo systemctl stop homelab-net-revert.timer homelab-net-revert.service homelab-net-apply.timer homelab-net-apply.service 2>/dev/null || true
sudo systemctl reset-failed 'homelab-net-*' 2>/dev/null || true
sudo rm -f /run/homelab-net-keep /run/homelab-net-apply.status /run/homelab-net-reverted
# The targets are frozen now, while the files on disk are still the new ones.
awk '$1=="address"||$1=="gateway"{print $1, $2}' /etc/network/interfaces.d/lan | sudo tee /run/homelab-net-target >/dev/null

sudo tee /run/homelab-net-revert.sh >/dev/null <<EOF
#!/bin/sh
# Same lock as the confirmation: only one of the two decides.
exec 9>/run/homelab-net.lock
flock 9
[ -e /run/homelab-net-keep ] && exit 0
touch /run/homelab-net-reverted
dns=\$(grep -m1 dns-nameservers /etc/network/interfaces.d/lan)
printf '%s\n' '# Ansible managed (role network)' 'allow-hotplug $IFACE' 'iface $IFACE inet static' \
  '	address $old_addr' '	gateway $old_gw' "\$dns" 'iface $IFACE inet6 auto' > /etc/network/interfaces.d/lan
ip -4 addr flush dev $IFACE
ip -4 route flush default dev $IFACE
ip addr add $old_addr dev $IFACE
ip route replace default via $old_gw dev $IFACE
EOF

# The session ends when the address changes, so the reload runs detached and
# records how it ended.
sudo tee /run/homelab-net-apply.sh >/dev/null <<EOF
#!/bin/sh
ip -4 addr flush dev $IFACE
ip -4 route flush default dev $IFACE
ifup --force $IFACE
echo \$? > /run/homelab-net-apply.status
EOF
sudo chmod 600 /run/homelab-net-revert.sh /run/homelab-net-apply.sh
sudo systemd-run --quiet --unit=homelab-net-revert --on-active=180 /bin/sh /run/homelab-net-revert.sh
sudo systemd-run --quiet --unit=homelab-net-apply --on-active=2 /bin/sh /run/homelab-net-apply.sh
echo "revert armed ($old_addr via $old_gw), reload scheduled"
REMOTE

echo "waiting for the node at $after"
last="no answer"
for _ in $(seq 1 30); do
  rc=0
  out=$(ssh "${ssh_opts[@]}" "$after" "IFACE=$iface CHECK_HOST=$check_host bash -s" 2>&1 <<'REMOTE'
[ ! -e /run/homelab-net-reverted ] || { echo "the revert already ran"; exit 7; }
[ "$(cat /run/homelab-net-apply.status 2>/dev/null)" = 0 ] || { echo "reload not finished or failed"; exit 3; }
want_addr=$(awk '$1=="address"{print $2}' /run/homelab-net-target)
want_gw=$(awk '$1=="gateway"{print $2}' /run/homelab-net-target)
ip -4 -o addr show dev "$IFACE" | grep -qw "$want_addr" || { echo "address $want_addr missing"; exit 4; }
ip -4 route show default | grep -q "via $want_gw" || { echo "default route via $want_gw missing"; exit 5; }
ping -c2 -W3 "$CHECK_HOST" >/dev/null || { echo "no reply from $CHECK_HOST"; exit 6; }
sudo flock /run/homelab-net.lock sh -c '[ ! -e /run/homelab-net-reverted ] && touch /run/homelab-net-keep' || { echo "the revert already ran"; exit 7; }
REMOTE
  ) || rc=$?
  if [ "$rc" = 0 ]; then
    echo "confirmed from $after: address, route and $check_host checked, the revert is cancelled"
    exit 0
  fi
  last=${out:-no answer}
  if [ "$rc" = 7 ]; then
    echo "not confirmed: the revert already ran, the node is back on its previous configuration" >&2
    exit 1
  fi
  sleep 3
done
echo "not confirmed ($last): the node reverts to its previous address on its own" >&2
exit 1
