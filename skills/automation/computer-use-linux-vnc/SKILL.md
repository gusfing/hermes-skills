---
name: computer-use-linux-vnc
description: Fix computer_use on Linux VNC when capture returns 0x0.
---

# computer_use on Linux with VNC

## When

- `computer_use` capture returns 0×0 or empty AX tree
- TigerVNC/Xvnc running on `:1` but cua-driver can't see it
- Gateway restart blocked from inside gateway process
- `computer_use` capture returns 0×0 despite VNC running and xhost granted
- `gnome-screenshot` fails with "cannot open display" on VNC
- VNC capture is the primary goal (user needs vision on desktop)

## Fix

### Root cause
`computer_use` capture returns 0×0 when the Hermes gateway process (which spawns cua-driver) does **not** have `DISPLAY` and `XAUTHORITY` set in its environment. The gateway service file `~/.config/systemd/user/hermes-gateway.service` must include these.

**Pitfall — env correct but capture still 0×0 (24-hour deadlock class):** Even after `DISPLAY=:1` and `XAUTHORITY` are verified in both gateway and cua-driver process envs, `computer_use capture` may still return 0×0. This session saw: Xvnc healthy on :1, VNC port 5901 listening, X11 Unix socket present, `xdpyinfo` connects (1 screen, 1920×1080), Xlib sees 33 X windows — yet `computer_use capture` returns 0×0 and `computer_use list_windows` returns 0 windows, every time. Root cause: cua-driver's X11 screen-capture implementation (`XGetImage`/`XOpenDisplay`) may not work against Xvnc's framebuffer/VNC extension. This is a **cua-driver/Xvnc compatibility gap**, not an env or VNC-running problem.

**Confirmation signal:** if a standard X11 screenshot tool also fails with "cannot open display :1" (e.g. `gnome-screenshot` → `Gtk-WARNING **: cannot open display: :1`), the VNC/X11 transport layer itself has a compatibility issue, not just cua-driver. When `xdpyinfo` works but screenshot apps fail, the X server accepts connection queries but doesn't support the framebuffer read operations those apps need.

### Diagnostic order
1. **Verify VNC is running:** `ss -tlnp | grep 5901`
2. **Check what env the gateway actually has:**
   ```bash
   GATEWAY_PID=$(pgrep -f "hermes_cli.main gateway run" | head -1)
   cat /proc/$GATEWAY_PID/environ | tr '\0' '\n' | grep -E "DISPLAY|XAUTH"
   ```
   If `DISPLAY` and `XAUTHORITY` are missing → gateway service needs patching (step 3).
3. **Set up X11 access** (one-time, as opc user):
   ```bash
   xhost +SI:localuser:opc
   ```
   Without this, Chrome exits immediately with "X connection error received" even though DISPLAY is set.
4. **Patch gateway service file** — add all three env vars:
   ```ini
   # ~/.config/systemd/user/hermes-gateway.service
   Environment="DISPLAY=:1"
   Environment="XAUTHORITY=/home/opc/.Xauthority"
   Environment="DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
   ```
   **Both `DISPLAY` and `XAUTHORITY` are required** — DISPLAY alone is not sufficient.
5. **Restart gateway from OUTSIDE the gateway process:**
   ```bash
   hermes gateway restart
   ```
   - Cannot restart from inside the gateway — it blocks with "Refusing to restart the gateway from inside the gateway process."
   - If `hermes gateway restart` is unavailable, kill the PID and let systemd auto-restart: `kill -9 $GATEWAY_PID`
   - On Oracle Linux, `systemctl --user` may fail with "No medium found" — use `kill` approach.
6. **Verify cua-driver inherited DISPLAY:**
   ```bash
   cat /proc/<cua-driver-pid>/environ | tr '\0' '\n' | grep DISPLAY
   ```
7. **Check display number matches VNC:** VNC on `:1` (port 5901) requires `DISPLAY=:1`. Mismatch (e.g. VNC on :5 but DISPLAY=:1) causes 0×0 captures.
8. **Test:** `computer_use capture mode=som` → should return real screenshot (not 0×0)

### If VNC is running and gateway has DISPLAY but capture still 0×0
**This is the hard case.** After confirming DISPLAY/XAUTHORITY are correct in both gateway and cua-driver env, and VNC is running, capture may still return 0×0 because cua-driver's X11 capture (`XGetImage`) doesn't work against Xvnc's framebuffer.

**Step-by-step for this case:**

1. **Rule out env first** (done above) — verify gateway and cua-driver both have `DISPLAY=:1` and `XAUTHORITY=/home/opc/.Xauthority` in `/proc/<pid>/environ`.

2. **Confirm VNC is actually running and accessible:**
   ```bash
   ss -tlnp | grep 5901          # VNC port listening
   ls -la /tmp/.X11-unix/X1      # X11 Unix socket exists
   DISPLAY=:1 XAUTHORITY=/home/opc/.Xauthority xdpyinfo | grep "number of screens"  # X connection works
   ```
   All three must pass.

3. **Test a standard X11 screenshot tool as a control:**
   ```bash
   DISPLAY=:1 XAUTHORITY=/home/opc/.Xauthority gnome-screenshot -w -f /tmp/test.png
   ```
   - If this also fails with "cannot open display :1" → the Xvnc framebuffer doesn't support screenshot read operations. **cua-driver capture will not work on this VNC setup.** Stop trying to fix VNC capture; switch to a different approach.
   - If this succeeds → cua-driver has a specific issue; try restarting it.

4. **If gnome-screenshot fails (most common on this host):** computer_use VNC capture is not viable. Fall back to:
   - **Headless Chrome + browser-harness CDP** (see browser-harness section below) — this worked for 24+ hours on this host when VNC capture failed
   - **Tailscale laptop Chrome** — connect to Chrome on the Windows laptop via Tailscale (CDP port forwarded) and drive it with browser-harness or browser tools
   - **VNC pixel capture** — use Python VNC client to grab frames from port 5901 directly

5. **Systemd drop-in for env (more reliable than editing the service file):**
   The gateway service file gets reverted between writes on this host. Use a drop-in instead:
   ```bash
   mkdir -p ~/.config/systemd/user/hermes-gateway.service.d
   cat > ~/.config/systemd/user/hermes-gateway.service.d/env.conf << 'EOF'
   [Service]
   Environment="DISPLAY=:1"
   Environment="XAUTHORITY=/home/opc/.Xauthority"
   Environment="DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
   EOF
   systemctl --user daemon-reload
   ```
   Drop-ins survive service-file rewrites. Verify with `systemctl --user cat hermes-gateway.service | grep Environment`.

6. **VNC restart caveats:**
   - `vncserver` wrapper adds `-tcp` to Xvnc args if `tcp` appears in `~/.vnc/config` — **this breaks Xvnc** ("Unrecognized option: -tcp"). Never add `tcp` to the VNC config. `-tcp` is not a valid Xvnc option.
   - When restarting Xvnc, clean up stale lock files: `rm -f /tmp/.X11-unix/X1 /tmp/.X1-lock`
   - After Xvnc restart, re-verify `xdpyinfo` connects before testing computer_use.

### STOP RULE (24-hour deadlock class)
After confirming DISPLAY/XAUTHORITY are correct in both gateway and cua-driver env, and VNC is running and `xdpyinfo` connects: **test a standard X11 screenshot tool as a control** before spending more time.

```bash
DISPLAY=:1 XAUTHORITY=/home/opc/.Xauthority gnome-screenshot -w -f /tmp/test.png
```

- If this also fails with "cannot open display :1" → the Xvnc framebuffer doesn't support screenshot read operations. **computer_use VNC capture will not work on this VNC setup. Stop debugging VNC.** Switch to a fallback:
  - **Headless Chrome CDP + browser-harness** — launch Chrome with `--headless --remote-debugging-port=9222`, connect browser-harness daemon, use helpers.py. No VNC needed.
  - **Tailscale laptop Chrome** — forward Chrome's CDP port from the Windows laptop over Tailscale.
  - **VNC pixel capture** — Python VNC client to port 5901, RFB handshake, framebuffer read (gives raw pixels without cua-driver).
- If `gnome-screenshot` succeeds → cua-driver has a specific issue; try restarting it or the gateway.

This is the 24-hour deadlock class seen on this host: Xvnc healthy, gateway env correct, `xdpyinfo` works, 33 X windows visible to Xlib — yet `computer_use capture` returns 0×0 and `gnome-screenshot` also fails. Root cause is cua-driver's X11 capture (`XGetImage`/`XOpenDisplay`) incompatibility with Xvnc's framebuffer/VNC extension. Further VNC restart attempts will not resolve this.

### Fallback approaches (when VNC capture is dead)
- **Headless Chrome CDP + browser-harness:** Launch Chrome with `--headless --remote-debugging-port=9222`, connect browser-harness daemon, use helpers.py for navigation/interaction. No VNC needed.
- **Tailscale laptop Chrome:** Forward Chrome's CDP port (9222) from the Windows laptop over Tailscale. Set `BU_CDP_URL=http://<laptop-ts-ip>:9222` and use browser-harness or browser tools.
- **VNC pixel capture:** Python VNC client connecting to localhost:5901, RFB protocol handshake, framebuffer read. Gives raw desktop pixels without cua-driver.
- **Local LLM inference (headless alternative):** When visual desktop access is unavailable and the user needs a model, run llama.cpp + GGUF directly. Skip LM Studio CLI/Desktop — the npm `lms` package is broken on this environment (missing `@lmstudio/cli` dependency) and LM Studio Desktop is an Electron GUI not suited for headless servers. See `references/gemma-4b-oracle-aarch64.md` for empirical speed data on this host.

### Fallback
  ```bash
  python3 -m pip install python-Xlib
  python3 -c "from Xlib import display; d=display.Display(':1'); root=d.screen().root; print(root.get_geometry())"
  ```
  `xdpyinfo` (from xorg-xdpyinfo package) also confirms X connectivity.

## Common failure: Python version mismatch for Xlib
`pip install python-Xlib` installs to Python 3.9 site-packages by default (on this Oracle Linux box). Hermes uses Python 3.11 venv. The module won't be importable from `python3` or `python3.11`. Fix:
```bash
python3 -m pip install python-Xlib    # installs to venv's Python 3.11
```

**0×0 capture despite VNC running:** If VNC is confirmed running and xhost is granted but capture still returns 0×0, the cua-driver process may not have inherited the correct DISPLAY. Verify with step 6. If DISPLAY is missing from the cua-driver process env, restart the gateway (step 5) so the new cua-driver inherits it. Also verify the VNC server display number matches what DISPLAY is set to — a mismatch (e.g. VNC on :5 but DISPLAY=:1) causes 0×0 captures.

## Running Chrome on VNC Desktop

Chrome launched on VNC without these env vars will exit immediately with "X connection error received" even though DISPLAY is set. Always include all four:

```bash
export DISPLAY=:1
export XAUTHORITY=/home/opc/.Xauthority
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
export HOME=/home/opc
/usr/bin/google-chrome-stable \
  --remote-debugging-port=9222 \
  --remote-debugging-address=0.0.0.0 \
  --user-data-dir=/home/opc/chrome-vnc-profile \
  --no-first-run \
  --no-default-browser-check \
  --disable-gpu \
  --disable-dev-shm-usage \
  --no-sandbox \
  --disable-software-rasterizer
```

**Critical:** Launch Chrome detached so it survives shell exit. On this environment, use `setsid ... &` or a systemd user service. Background processes launched with `&` alone get killed when the session ends.

**Systemd user service fallback:** Oracle Linux's `systemctl --user` may fail with "No medium found" (no dbus session). In that case, verify Chrome is alive via:
```bash
ps aux | grep chrome | grep -v grep | wc -l
curl -s http://127.0.0.1:9222/json/version | python3 -m json.tool | head -5
```

## Fallback

```bash
export DISPLAY=:1
python3 -c "from PIL import ImageGrab; ImageGrab.grab().save('/tmp/vnc.png')"
# vision_analyze /tmp/vnc.png
```

## Architecture

Server = brain (Hermes, 9router, VNC GUI on :1). PC = browser (Chrome CDP 9222 via Tailscale) + storage. browser-harness on server connects to PC Chrome via BU_CDP_URL=http://<PC_TS_IP>:9222.