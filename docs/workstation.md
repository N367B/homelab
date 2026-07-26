# Workstation Setup Guide (Day 0 Admin PC)

How to set up a new Windows + WSL2 workstation (e.g. laptop or secondary PC) to manage the homelab.

---

## 1. Prerequisites (WSL Packages)

In your WSL distribution (Debian / Ubuntu), install the base utilities and Ansible:

```sh
sudo apt update && sudo apt install -y make git python3 python3-pip ansible wireguard-tools rsync
```

### Install SOPS

Install the Renovate-managed version of `sops` (`v3.13.2`):

```sh
curl -LO https://github.com/getsops/sops/releases/download/v3.13.2/sops-v3.13.2.linux.amd64
sudo mv sops-v3.13.2.linux.amd64 /usr/local/bin/sops
sudo chmod +x /usr/local/bin/sops
```

---

## 2. Secrets & SOPS Age Key

SOPS needs the master age private key to decrypt secrets at play time:

```sh
mkdir -p ~/.config/sops/age
nano ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
```

> **Note**: Retrieve the master age private key from **Proton Pass** (or paper backup). Public key: `age1rtp96zhxs6dwnx5c0xqanf2aamfkgmkntdakn95z3efglcyvhdvs0zzsn4`.

---

## 3. SSH Setup & Automatic Windows <-> WSL Sync

### Generate Host SSH Key
Generate a dedicated keypair for the workstation:

```sh
ssh-keygen -t ed25519 -f ~/.ssh/homelab -C "noe@<hostname>"
```

Add the generated public key (`~/.ssh/homelab.pub`) to `admin_authorized_keys` in `configure/group_vars/all.yml` and run `make deploy`.

### Automatic SSH Sync Script (`~/bin/sync-ssh`)
To keep `~/.ssh` synchronized between Windows (`C:\Users\<User>\.ssh`) and WSL with automatic local Git versioning, create `~/bin/sync-ssh`:

```sh
mkdir -p ~/bin
nano ~/bin/sync-ssh
chmod +x ~/bin/sync-ssh
```

**Script contents (`~/bin/sync-ssh`)**:

```bash
#!/bin/bash
# Two-way sync of ~/.ssh (WSL) <-> Windows .ssh, versioned in git.
# Newest file wins in both directions; known_hosts stays per-side.
set -e
WIN="/mnt/c/Users/Bodin/.ssh"
WSL="$HOME/.ssh"
EXCLUDES=(--exclude 'known_hosts*' --exclude '.git*' --exclude '.overwritten' --exclude 'agent.*' --exclude '*.sock' --exclude 'control-*')

exec 9>"$WSL/.sync-ssh.lock"
flock -n 9 || exit 0

# Probe clock skew vs Windows
touch "$WIN/.timeprobe" 2>/dev/null || exit 0
skew=$(( $(stat -c %Y "$WIN/.timeprobe") - $(date +%s) ))
rm -f "$WIN/.timeprobe"
[ "${skew#-}" -gt 2 ] && echo "sync-ssh: WARNING ${skew}s clock skew vs Windows" >&2

snapshot() {
    git -C "$WSL" add -A
    git -C "$WSL" diff --cached --quiet || git -C "$WSL" commit -qm "$1 $(date '+%F %H:%M')"
}

snapshot "pre-sync"

mkdir -p "$WSL/.overwritten"
for f in "$WIN"/*; do
    b=$(basename "$f")
    case "$b" in known_hosts*|.git*|.overwritten|agent.*|*.sock|control-*) continue;; esac
    w="$WSL/$b"
    if [ -f "$w" ] && [ "$w" -nt "$f" ] && ! cmp -s "$f" "$w"; then
        cp -p "$f" "$WSL/.overwritten/$b"
    fi
done
snapshot "windows versions before overwrite"

rsync -au "${EXCLUDES[@]}" "$WIN/" "$WSL/"
rsync -au "${EXCLUDES[@]}" "$WSL/" "$WIN/"
chmod 700 "$WSL"
find "$WSL" -maxdepth 1 -type f ! -name '*.pub' -exec chmod 600 {} +
chmod 644 "$WSL"/*.pub 2>/dev/null || true
snapshot "post-sync"
```

### Auto-launch on shell startup
Add the background execution hook to `~/.bashrc`:

```sh
echo '(~/bin/sync-ssh >/dev/null 2>&1 &) # auto-sync ssh keys with Windows' >> ~/.bashrc
```

---

## 4. Repository Setup

Clone the homelab repository into Linux native filesystem (`~/homelab` recommended for performance):

```sh
git clone git@github.com:N367B/homelab.git ~/homelab
cd ~/homelab
make deps
```

---

## 5. Verification

Verify connectivity and SOPS decryption:

```sh
make ping
make check
```
