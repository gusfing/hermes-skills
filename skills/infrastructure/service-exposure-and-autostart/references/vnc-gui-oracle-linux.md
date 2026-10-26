# VNC GUI on Oracle Linux aarch64 — worked session notes

## Context
Oracle Cloud Free Tier ARM instance (aarch64), 4GB RAM, Oracle Linux 9.
Need GUI desktop accessible over Tailscale for browser automation / visual tasks.

## What worked

### 1. Install GNOME (Server with GUI group)
```bash
sudo dnf group install -y "Server with GUI"
sudo dnf install -y tigervnc-server dbus-x11
```
Note: XFCE not available in Oracle Linux 9 repos. GNOME is the only desktop option via `dnf group`.

### 2. VNC password
```bash
mkdir -p ~/.vnc
echo "yourpassword" | vncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd
```

### 3. xstartup for GNOME
```bash
cat > ~/.vnc/xstartup << 'EOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec gnome-session
EOF
chmod +x ~/.vnc/xstartup
```

### 4. Systemd service (user unit won't work for X11)
Create `/etc/systemd/system/vncserver@:1.service`:
```ini
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
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vncserver@:1
sudo systemctl start vncserver@:1
```

### 5. Firewall
```bash
sudo firewall-cmd --permanent --add-port=5901/tcp
sudo firewall-cmd --reload
```

### 6. Tailscale access
```bash
tailscale ip -4
# Connect to <tailscale-ip>:5901 with VNC viewer
```

## Pitfalls

| Issue | Fix |
|-------|-----|
| `startxfce4: not found` | XFCE not in Oracle Linux repos; use `gnome-session` |
| `libEGL warning: failed to open /dev/dri/card0` | Headless ARM instance — no GPU. Software rendering works but logs warnings. Ignore. |
| systemd PID file mismatch | VNC creates `hostname:1.pid` not `hostname::1.pid`. Service shows "activating" but works. Check `ss -tlnp \| grep 5901` and logs. |
| User unit vs system unit | X11 needs system unit (`/etc/systemd/system/`) not user unit (`~/.config/systemd/user/`). |
| 4GB RAM with GNOME + VNC + Hermes | Tight. Monitor with `free -h`. Consider lighter WM if memory pressure. |

## Verification
```bash
# Check VNC listening
ss -tlnp | grep 5901
# Check log
cat ~/.vnc/$(hostname):1.log
# Test from Tailscale peer
# VNC viewer -> <tailscale-ip>:5901
```

## Related
- Use with `computer-use` skill for browser automation on the VNC desktop
- Tailscale Serve not needed — VNC runs on 5901 directly over tailnet
- Password auth at VNC layer; no application-level auth needed