---
name: oracle-hermes-deployment
description: >-
  Deploy and reset Hermes Agent on Oracle Cloud Free Tier ARM64 VPS
  (Oracle Linux). Covers clean slate, disk expansion, fresh clone,
  venv setup, launcher patching, verification, and migration from
  x86_64 Hermes installs. Use when user asks to set up Hermes on
  Oracle, clone fresh, fix broken installs, or clone the full install
  to the Oracle dashboard.
---

# Oracle Hermes Deployment

## User Style Preference

User is action-first and direct. When something fails or is blocked, pivot immediately to the fastest fallback instead of explaining what went wrong. Prefer giving direct commands for the user to run rather than narrating steps.

## Dashboard Access

Hermes dashboard host-header check rejects Tailscale serve. Reliable path is SSH port forwarding from Windows:

```powershell
Start-Process ssh -ArgumentList "-N","-L","9120:127.0.0.1:9120","-i","C:\Users\ks209\Downloads\ssh-key-2026-08-01 (2).key","opc@137.23.36.156" -WindowStyle Hidden
```

Then open `http://localhost:9120` on Windows. Keep the SSH session open while using the dashboard.

## Fresh Reset Procedure

When user requests a clean slate on Oracle VPS (`opc@137.x.x.x`):

1. Preserve SSH keys before wiping home:
   ```bash
   cp ~/.ssh/authorized_keys /tmp/save_auth_keys
   ```
2. Kill stray processes:
   ```bash
   pkill -9 hermes node 2>/dev/null || true
   ```
3. Wipe home:
   ```bash
   sudo rm -rf /home/opc/* /home/opc/.[!.]* /home/opc/..?*
   ```
4. Restore SSH and verify access from remote before proceeding.

## Disk Expansion

Oracle shows misleading `df` output after block-volume resize.

- Resize partition: `sudo fdisk /dev/sda` → delete partition 3, recreate with same start sector, full end sector.
- Reread partition table: `sudo partx -u /dev/sda`
- Resize PV: `sudo pvresize /dev/sda3`
- Resize LV: `sudo lvextend -l +100%FREE /dev/ocivolume/root`
- Grow filesystem: `sudo xfs_growfs /`

## Hermes Install / Reset

Preferred path: clone repo, use uv-managed Python 3.11.

```bash
rm -rf ~/.hermes/hermes-agent
GIT_TERMINAL_PROMPT=0 git clone --depth 1 https://github.com/nousresearch/hermes-agent.git ~/.hermes/hermes-agent
cd ~/.hermes/hermes-agent
~/.hermes/bin/uv venv .venv
~/.hermes/bin/uv pip install -e '.[all]' --python .venv/bin/python
```

## Launcher Patch

The `hermes` launcher uses `#!/usr/bin/env python3` which resolves to system Python 3.9 on Oracle, breaking the install.

Patch after every fresh clone:

```bash
sed -i '1s|.*|#!/home/opc/.hermes/hermes-agent/.venv/bin/python3|' ~/.hermes/hermes-agent/hermes
chmod +x ~/.hermes/hermes-agent/hermes
```

## PATH Setup

Oracle login shells don't always source `.bashrc`. Add PATH to both `.bashrc` and `.bash_profile`:

```bash
echo 'export PATH=$HOME/.hermes/hermes-agent:$HOME/.hermes/bin:$HOME/.local/bin:$PATH' >> ~/.bashrc
echo 'export PATH=$HOME/.hermes/hermes-agent:$HOME/.hermes/bin:$HOME/.local/bin:$PATH' >> ~/.bash_profile
```

## Two Launchers — Patch Both

After every fresh clone, patch BOTH launcher scripts:

- `~/.hermes/hermes-agent/hermes` — the repo launcher
- `~/.local/bin/hermes` — the installer symlink/wrapper

Use sed for the wrapper too:

```bash
sed -i 's|venv/bin/python|.venv/bin/python3|' ~/.local/bin/hermes
```

## Venv Name Change

Recent Hermes installer uses `.venv` (dot-prefixed), not `venv`. Patch the first line of both launchers:

```bash
sed -i '1s|.*|#!/home/opc/.hermes/hermes-agent/.venv/bin/python3|' ~/.hermes/hermes-agent/hermes
chmod +x ~/.hermes/hermes-agent/hermes
```

## Verification

```bash
hermes --version   # expect v0.19.1+ with Python 3.11.15
hermes doctor      # all green
hermes chat        # interactive CLI works
```

## Pitfalls

- `df -h` shows 100% even after cleanup on XFS; use `df -i` to check inode exhaustion.
- Inode exhaustion is caused by node_modules dirs with millions of small files, not just disk bytes.
- `pvresize` fails with "Couldn't create temporary archive name" until partition is reread with `partx -u`.
- Hermes dashboard host-header check blocks Tailscale serve; use SSH port forwarding instead.
- Oracle default Node.js v20 is too old; uv-installed Node 22 is bundled by Hermes installer.
- Two `hermes` launchers exist: `~/.hermes/hermes-agent/hermes` (repo) and `~/.local/bin/hermes` (wrapper). Both must point to `.venv/bin/python3`.
- `.bashrc` changes don't apply to login shells; always add PATH to `.bash_profile` too.
- **x86_64 → ARM64 migration:** `node_modules`, browser binaries (`.agent-browser`, `.cache/puppeteer`), uv caches, and the Python venv cannot be copied across architectures. Rebuild them on Oracle with `npm install` / `playwright install` / `uv pip install`. Only the data/config layers are portable.
- **Portable layers:** skills, plugins, chrome-profiles, `.camofox`, outreach stack, state, spawn-trees. Use `tar` to bundle and transfer these.
- **Chrome profiles / Camofox sessions:** these are portable across machines; WhatsApp login state in `chrome-profiles/wa_account_a` carries over after migration.
- **Outreach stack:** after extracting on Oracle, run `cd /opt/data/outreach && npm install` to rebuild ARM-native deps.
- **mesa_shader_cache:** skip it; it regenerates on first GPU use and is architecture-specific.
- **journalctl vacuum may fail without sudo** for `/run/log/journal/*` owned by `systemd-journal:root:2750`; old archives are not user-deletable and need root if really required.
- **Docker socket access from `opc`:** `docker ps` will show permission denied unless `opc` is in the `docker` group or using root. Service itself may still be healthy; this is not a disk/speed issue. Diagnostic sequence: `ls -la /var/run/docker.sock` (should be `srw-rw---- root docker`), `id` (check `docker` group absent), then use `sudo docker ...` or `sudo docker compose ...` as the immediate workaround. To persist without sudo, `sudo usermod -aG docker opc` then re-login.
- **Performance baseline (2026-08-15 after cleanup):** disk 26–28%, load ~0.03, RAM ~2.6G/10G, swap 38M. Use this as healthy reference.

## Performance cleanup

Safe space-reclaim recipe on a loaded Oracle VPS without service disruption: `references/oracle-performance-cleanup.md`
- **journalctl vacuum may fail without sudo** for `/run/log/journal/*` owned by `systemd-journal:root:2750`; old archives are not user-deletable and need root if really required.
- **Docker socket access from `opc`:** `docker ps` will show permission denied unless `opc` is in the `docker` group or using root. Service itself may still be healthy; this is not a disk/speed issue. Diagnostic sequence: `ls -la /var/run/docker.sock` (should be `srw-rw---- root docker`), `id` (check `docker` group absent), then use `sudo docker ...` or `sudo docker compose ...` as the immediate workaround. To persist without sudo, `sudo usermod -aG docker opc` then re-login.
- **Performance baseline (2026-08-15 after cleanup):** disk 26–28%, load ~0.03, RAM ~2.6G/10G, swap 38M. Use this as healthy reference.

## 9router — operational lifecycle

See `references/9router-operational-lifecycle.md` for the full failure-diagnosis flow, DB driver resolution (including ABI mismatch rebuild), crash-loop recovery, verified systemd configuration, and CLI token API access pattern.

Key signatures for quick triage:

- **[DB] No SQLite driver available** — check `references/9router-operational-lifecycle.md` § "ABI mismatch — the real cause". Most often a Node 22 vs Node 20 ABI mismatch in `~/.9router/runtime/node_modules/better-sqlite3`. Fix: rebuild with system node-gyp + symlink into app's node_modules.
- **dashboardGuard "Local only: CLI token required" / 403** — CLI token required for tunnel/API endpoints. Compute from `~/.9router/machine-id` + `~/.9router/auth/cli-secret` (sha256, first 16 chars). Send as `x-9r-cli-token` header.
- **203/EXEC in systemd** — service file uses `~/.hermes/node/bin/node`; switch to `/usr/bin/node`.
- **Clean exit, restart loop** — missing `--tray` flag; add it to ExecStart.
- **ERR_CONNECTION_RESET in browser** — 9router crashed mid-request; check NRestarts, health endpoint, then journal.
- **Tunnel enable times out** — cloudflared quick tunnel restarts on each enable; the URL changes. Check `api/tunnel/status` for current URL.

### SSH tunnel (Windows, both ports)

```powershell
ssh -L 9120:127.0.0.1:9120 -L 20128:127.0.0.1:20128 -i "C:\Users\ks209\Downloads\ssh-key-2026-08-01 (2).key" -p 22 opc@137.23.36.156
```

Background mode: add `-f -N`.

### browser-harness (CDP Chrome)

Google Chrome 151 headless with remote debugging on port 9222:
```bash
google-chrome --remote-debugging-port=9222 --no-first-run --no-default-browser-check --disable-extensions --disable-gpu --headless=new --no-sandbox --disable-dev-shm-usage about:blank &
```

browser-harness configured via `.env`:
```bash
# /home/opc/workspace/browser-harness/.env
BU_CDP_URL=http://127.0.0.1:9222
```

Verified working: `./browser-harness --doctor` shows all green, navigation works.

## VNC Server (GUI access)

Oracle Linux 9 ARM64: use "Server with GUI" group (GNOME), **xfce4 not available in repos**.

```bash
# Install GUI stack
sudo dnf group install -y "Server with GUI"
sudo dnf install -y tigervnc-server dbus-x11

# Set VNC password
mkdir -p ~/.vnc
echo "yourpassword" | vncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd

# xstartup for GNOME
cat > ~/.vnc/xstartup << 'EOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec gnome-session
EOF
chmod +x ~/.vnc/xstartup

# Firewall
sudo firewall-cmd --permanent --add-port=5901/tcp
sudo firewall-cmd --reload

# Systemd service
sudo tee /etc/systemd/system/vncserver@:1.service > /dev/null << 'EOF'
[Unit]
Description=TigerVNC Server for opc
After=network.target

[Service]
Type=forking
User=opc
Group=opc
WorkingDirectory=/home/opc
PIDFile=/home/opc/.vnc/%H:%i.pid
ExecStartPre=-/usr/bin/vncserver -kill :1
ExecStart=/usr/bin/vncserver :1 -geometry 1920x1080 -depth 24
ExecStop=/usr/bin/vncserver -kill :1
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vncserver@:1
sudo systemctl start vncserver@:1
```

**Connect:** `100.93.145.31:5901` (or `:1`) with VNC viewer, password `yourpassword`.
Resolution: 1920×1080. Auto-starts on boot.