# Computer Use (cua-driver) on Oracle Linux aarch64 — worked session notes

## Context
Oracle Cloud Free Tier ARM instance (aarch64), Oracle Linux 9.
Setting up background desktop automation via `computer_use` tool (cua-driver).

## What worked

### 1. Install cua-driver
```bash
hermes computer-use install
```
Installs Rust binary `cua-driver` to `~/.local/bin/cua-driver` (v0.20.0 for aarch64).

### 2. Verify installation
```bash
hermes computer-use doctor
# Should report: "cua-driver: installed" and health checks
```

### 3. VNC desktop for GUI automation
VNC server running on `:1` (port 5901) with GNOME desktop.
- Connect: `100.93.145.31:5901` (Tailscale IP)
- Password: `yourpassword`
- Resolution: 1920x1080

### 4. Hermes gateway restart required
The `computer_use` tool is configured in `~/.hermes/config.yaml` under `platform_toolsets.cli` but **the running gateway doesn't pick it up until restart**.

```bash
# From a separate shell (not inside Hermes gateway process):
hermes gateway restart

# Or if using systemd:
systemctl --user restart hermes-gateway
```

**Critical:** Running `cua-driver` or any binary from inside the Hermes gateway process is blocked (SIGTERM propagation). Must run restart from separate shell.

### 5. After restart
The `computer_use` tool becomes available in Hermes sessions:
- `capture` — screenshot with SOM overlays + AX tree
- `click` — by element index or coordinate
- `type` — text input
- `key` — keyboard shortcuts
- `scroll` — viewport scrolling
- `drag` — drag and drop
- `list_apps` / `focus_app` — app management

## Configuration in config.yaml
```yaml
platform_toolsets:
  cli:
    - computer_use  # must be present
    - browser
    - terminal
    # ... other tools
```

## Pitfalls

| Issue | Fix |
|-------|-----|
| `computer_use` tool not found | Restart Hermes gateway from separate shell |
| `cua-driver not installed` | Run `hermes computer-use install` |
| Captures return empty / "no on-screen window" | On Linux headless: X11 DISPLAY must be set. VNC provides this. |
| Click has no effect | Read structured verdict: `effect: "unverifiable"` → re-capture. `effect: "suspected_noop"` → climb ladder: pixel coords → typed page → foreground |
| `cua-driver` commands blocked inside gateway | Run from separate terminal, not inside Hermes session |

## Verification
```bash
# Check cua-driver installed
ls -la ~/.local/bin/cua-driver

# Check config has computer_use
grep -A 20 "platform_toolsets" ~/.hermes/config.yaml

# After gateway restart, test in new Hermes session
# computer_use(action="capture", mode="som", app="Chrome")
```

## Related
- `service-exposure-and-autostart/references/vnc-gui-oracle-linux.md` — VNC setup
- `computer-use` skill (autonomous-ai-agents/computer-use) — full action vocabulary
- cua-driver skill pack: `/home/opc/.local/bin/cua-driver skills install`