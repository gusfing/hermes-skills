---
name: remote-server-provisioning
description: >
  Provision and control a remote Linux server over SSH for deploying tools,
  outreach stacks, and agent runtimes. Covers Oracle Cloud Free Tier,
  key-based auth, disk expansion, and installing Hermes/Playwright on ARM
  or AMD instances.
---

# Remote Server Provisioning

## When to use

- User gives SSH access to a remote VPS
- Need to install Hermes, Playwright, Node.js tooling
- Disk/partition needs expansion after resize
- Fresh start requested ("delete everything, install new")

## Key-based auth flow

1. User generates keypair locally (PuTTYgen, ssh-keygen)
2. User provides PUBLIC key content
3. On remote server:
   ```bash
   mkdir -p ~/.ssh && chmod 700 ~/.ssh
   echo "ssh-ed25519 AAAA..." >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```
4. Agent generates matching private key on this container for SSH access

## Disk expansion on Oracle Linux (XFS + LVM)

Oracle Free Tier requires manual LVM extension after console resize.

**Pre-flight checks:**
```bash
df -h /home && df -i /home
```

If `df -i` shows 100% inode use but `df -h` shows low usage, inode exhaustion is the real blocker — not space. Fix inodes first.

**Expansion sequence:**
```bash
# 1. Verify partition state
sudo fdisk -l /dev/sda | grep sda3

# 2. If partition is smaller than disk, resize it
sudo fdisk /dev/sda <<EOF
d
3
n
3
<start-sector>

w
EOF

# 3. Re-read partition table
sudo partx -u /dev/sda

# 4. Verify partition grew
sudo fdisk -l /dev/sda | grep sda3

# 5. Resize PV (may fail if inodes exhausted; kill inode hog first)
sudo pvresize /dev/sda3

# 6. Extend LV
sudo lvextend -l +100%FREE /dev/<vg>/root

# 7. Grow XFS
sudo xfs_growfs /
```

**Pitfall:** `pvresize` writes temp metadata and can fail with “No space left on device” when inodes are exhausted, even if disk blocks are free. Always check `df -i` first.

## Inode exhaustion recovery

Common after failed installs with millions of small files:

```bash
# Check inode usage
df -i /

# Find inode hogs
find /home -xdev -type f | wc -l

# Kill processes using the dir, then remove
sudo pkill -9 <process>
sudo rm -rf /path/to/hog
```

## Hermes on ARM/AMD Linux

- Oracle Linux ARM needs venv Python 3.11+ (system Python may be 3.9)
- Fresh installs create `.venv`, not `venv`. Fix launcher shebang:
  ```bash
  sed -i '1s|.*|#!/home/opc/.hermes/hermes-agent/.venv/bin/python3|' ~/.hermes/hermes-agent/hermes
  ```
- Two launcher scripts may exist: `~/.hermes/hermes-agent/hermes` and `~/.local/bin/hermes`. Fix both if needed.
- Add to PATH in `.bash_profile` as well as `.bashrc` because Oracle login shells don’t always source `.bashrc`:
  ```bash
  echo 'export PATH=$HOME/.hermes/hermes-agent:$HOME/.local/bin:$PATH' >> ~/.bash_profile
  ```
- SQLite 3.34.1 warning on Oracle is cosmetic; Hermes works. Fix with `hermes update` if desired.

## Dashboard access on Oracle Linux

`hermes dashboard` binds `127.0.0.1` and validates `Host`. Tailscale serve changes that header, so it returns `Invalid Host header`. Best path is SSH port forwarding or direct CLI.

**Windows SSH tunnel command:**
```powershell
Start-Process ssh -ArgumentList "-N","-L","9120:127.0.0.1:9120","-i","C:\path\to\key","opc@host"
```
Then open **http://localhost:9120**

## Fresh-start procedure

User may request “delete everything, fresh start.” Do this in one SSH session:

```bash
# 1. Backup SSH keys
cp ~/.ssh/authorized_keys /tmp/save_auth_keys
pkill -9 hermes node omniroute 2>/dev/null

# 2. Wipe home (preserves /home itself)
sudo rm -rf /home/opc/* /home/opc/.[!.]* /home/opc/..?*

# 3. Restore SSH
mkdir -p ~/.ssh
mv /tmp/save_auth_keys ~/.ssh/authorized_keys
chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys
```

Then run Hermes install script and apply the launcher/PATH fixes above.

## Outreach stack deployment

1. Tar the outreach directory on this container
2. SCP to remote: `scp /tmp/outreach.tar.gz user@host:~/`
3. Extract: `tar xzf ~/outreach.tar.gz -C ~/`
4. Patch hardcoded paths in scripts to relative `require('playwright')`
5. Install Playwright: `npm install playwright && npx playwright install chromium`
6. Test tools: `node scripts/x_poster.js --help`

## Pitfalls

- Do NOT assume docker-compose is available inside Docker containers
- Do NOT blindly retry SSH timeouts — check connectivity first
- XFS `df` can show 100% while writes succeed; check `df -i` for inodes
- Hermes `--insecure` flag is deprecated; public binds require auth
- Never share private key contents
