# Linux Headless Server: VNC + computer_use Setup (Oracle Linux 9 aarch64)

For running `computer_use` on a headless Linux server.

## Prerequisites

```bash
# Install desktop environment + VNC (Oracle Linux 9)
sudo dnf group install -y "Server with GUI"
sudo dnf install -y tigervnc-server dbus-x11

# Set VNC password
mkdir -p ~/.vnc
echo "yourpassword" | vncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd

# Configure xstartup for GNOME (xfce4 not in Oracle Linux repos)
cat > ~/.vnc/xstartup << 'EOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec gnome-session
EOF
chmod +x ~/.vnc/xstartup
```

## Start VNC Server

```bash
# Test manually first
vncserver :1 -geometry 1920x1080 -depth 24

# Or as systemd service (auto-start on boot)
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

# Firewall
sudo firewall-cmd --permanent --add-port=5901/tcp
sudo firewall-cmd --reload
```

Connect via VNC viewer: `<tailscale-ip>:5901` (or `:1`)

## Install cua-driver

```bash
hermes computer-use install
# Installs cua-driver-rs to ~/.local/bin/cua-driver
```

## Enable computer_use Tool

The `computer_use` tool is listed in `config.yaml` under `platform_toolsets.cli` but requires a **gateway restart** to load:

```bash
# From a SEPARATE SSH session (not through the gateway):
hermes gateway restart
# OR
systemctl --user restart hermes-gateway
```

**Cannot restart from inside the gateway process** — it blocks with SIGTERM propagation error.

Workaround: schedule via cron from within gateway:
```bash
cronjob create --name restart-gateway --schedule "2026-08-18T22:35:00" --script "systemctl --user restart hermes-gateway" --no-agent true
```

## Verify

```bash
# After gateway restart, computer_use tool should appear
# In Hermes session:
computer_use(action="capture", mode="som")
```

## Architecture Notes (This Session)

| Component | Location |
|-----------|----------|
| Hermes Agent + 9router | Oracle server (brain) |
| Chrome CDP (port 9222) | Windows PC (browser) |
| VNC Server (port 5901) | Oracle server (GUI for computer_use) |
| Tailscale | Connects all (100.93.145.31) |

## Troubleshooting

- **No xfce4 in Oracle Linux** → Use "Server with GUI" group (GNOME)
- **libEGL warning: failed to open /dev/dri/card0** → Normal on headless, ignores
- **computer_use not in tool list** → Gateway not restarted yet
- **cua-driver not found** → Run `hermes computer-use install`
- **VNC shows blank screen** → Check xstartup uses `gnome-session` not `startxfce4`