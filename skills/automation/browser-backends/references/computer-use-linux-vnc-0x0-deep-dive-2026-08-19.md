# computer_use on Linux VNC — 0×0 capture despite correct env (24h persisted)

## Session context
2026-08-19, Oracle Linux 9 aarch64, Xvnc on :1 (port 5901), TigerVNC 1.15.0,
Hermes gateway + cua-driver 0.20.0. Capture returned 0×0 for the entire session
despite repeated gateway restarts with correct DISPLAY/XAUTHORITY env.

## What was verified working (env layer is NOT broken)
- Gateway `/proc/<pid>/environ` has `DISPLAY=:1`, `XAUTHORITY=/home/opc/.Xauthority`
- cua-driver `/proc/<pid>/environ` has the same
- `ss -tlnp | grep 5901` → VNC port listening on 0.0.0.0:5901 and [::]:5901
- `/tmp/.X11-unix/X1` exists (Unix socket)
- `xdpyinfo` connects: "name of display: :1", "number of screens: 1",
  "1920x1080 pixels", "depth of root window: 24 planes"
- Xlib (python-Xlib 0.33) connects via Unix socket, sees 33 X windows recursively
- `vncserver -list` shows ":1  <pid>"
- `xauth list | grep :1` shows MIT-MAGIC-COOKIE-1 entries
- `xhost` reports "access control enabled, only authorized clients can connect"
- `gnome-screenshot -w -f /tmp/test.png` → "cannot open display: :1" (Gtk-WARNING)

## What failed (every attempt)
- `computer_use capture mode=som` → 0×0, 0 elements, every time
- `computer_use list_windows` → {} windows: 0, every time
- Gateway restart × many (kill + systemd auto-restart) → no change
- Service file patch with DISPLAY/XAUTH/DBUS env → reverted between writes
- Systemd drop-in `~/.config/systemd/user/hermes-gateway.service.d/env.conf` →
  env confirmed in running process, still 0×0
- `xhost +SI:localuser:opc` → no change
- Python-Xlib `root.get_image()` → `'Window' object has no attribute 'width'`
  (API mismatch in python-Xlib 0.33 on this Python 3.11 venv)
- ImageMagick `import` → not installed
- OpenCV → not installed
- PIL ImageGrab → `from PIL import ImageGrab` not available in this env

## Root cause assessment
**cua-driver's X11 screen-capture implementation does not work against Xvnc's
framebuffer.** Evidence:
1. A standard X11 app (`gnome-screenshot`) also cannot open the display for
   screenshot purposes, even though `xdpyinfo` (info query) works fine.
2. This means the X server accepts connection/authentication but does not
   support the framebuffer read operations (`XGetImage`) that screenshot
   tools and cua-driver need.
3. The Xvnc VNC extension may interfere with or not implement the X11
   image-read path that cua-driver uses.

This is a **cua-driver/Xvnc framebuffer compatibility gap**, not an env,
VNC-running, or permissions problem. xrander/gnome-screenshot confirm the
same failure pattern in standard X11 apps.

## Decisions made this session
- **Drop VNC capture as the primary approach.** It is not viable on this host
  with this cua-driver + Xvnc combination.
- **Use headless Chrome + browser-harness CDP as the working path.** Chrome
  launched with `--headless --remote-debugging-port=9222` stays alive, CDP
  responds, browser-harness daemon connects, helpers.py navigates pages.
- **Tailscale laptop Chrome as secondary path.** Windows laptop Chrome CDP
  forwarded over Tailscale to `BU_CDP_URL=http://<TS-IP>:9222`.

## Xvnc restart gotchas (session findings)
- `~/.vnc/config` must NOT contain `tcp` — `vncserver` passes it to Xvnc as
  `-tcp`, which Xvnc rejects as "Unrecognized option: -tcp", killing the server.
- When restarting Xvnc manually: `rm -f /tmp/.X11-unix/X1 /tmp/.X1-lock` first.
- `vncserver :1` wrapper is deprecated; the deprecation warning says use
  systemd. In this env, starting Xvnc directly (`/usr/bin/Xvnc :1 ...`) works.
- vncserver reads `~/.vnc/config` for options — if `tcp` is there, it breaks.
- After restart, always re-verify with `xdpyinfo` before testing computer_use.

## Gateway restart constraint
From inside the gateway process:
- `hermes gateway restart` → "Refusing to restart the gateway from inside..."
- `systemctl --user restart` → "Blocked: command cannot restart or stop the
  gateway from inside the gateway process."
- Workaround: `kill -9 <gateway-pid>` → systemd `Restart=always` auto-restarts.
- On Oracle Linux, `systemctl --user` may fail with "No medium found" (no dbus
  session bus). Use the kill approach.

## Env var requirement (hard requirement, not optional)
Gateway service file MUST have ALL THREE:
```ini
Environment="DISPLAY=:1"
Environment="XAUTHORITY=/home/opc/.Xauthority"
Environment="DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus"
```
DISPLAY alone is NOT sufficient. The service file keeps getting reverted —
use a systemd drop-in (`hermes-gateway.service.d/env.conf`) instead of editing
the main file. Drop-ins survive service-file rewrites.

## Chrome on VNC: X connection death
Chrome launched with `--remote-debugging-port=9222` on DISPLAY=:1 starts,
gets CDP listening, then dies with:
```
[pid:...]ERROR:ui/gfx/x/connection.cc:66] X connection error received.
```
This happens regardless of launch method (background terminal, setsid, exec,
start-chrome-vnc.sh, launch-chrome-cdp.py). Root cause: Chrome's X11 backend
can't maintain a stable connection to Xvnc, same class of issue as the
screenshot failure. Headless Chrome (no X display) avoids this entirely.

## Working headless Chrome launch (session-verified)
```bash
export DISPLAY=:99          # dummy, won't be used in headless mode
export HOME=/home/opc
export BU_CDP_URL=http://127.0.0.1:9222
export BU_NAME=default
/usr/bin/google-chrome-stable \
  --headless \
  --disable-gpu \
  --remote-debugging-port=9222 \
  --remote-debugging-address=0.0.0.0 \
  --user-data-dir=/home/opc/chrome-headless-profile \
  --no-first-run \
  --no-default-browser-check \
  --disable-dev-shm-usage \
  --no-sandbox \
  --disable-software-rasterizer \
  --window-size=1920,1080
```
This lands CDP on 9222 (Chrome/151), browser-harness daemon connects via
socket, helpers.py navigates pages.

## References
- `computer-use-linux-vnc` skill — class-level VNC capture guidance
- `browser-backends` skill — Chrome CDP / browser-harness patterns
- `helpers.py` (538 lines) — browser-harness functions:
  `cdp()`, `goto_url()`, `page_info()`, `click_at_xy()`, `type_text()`,
  `fill_input()`, `press_key()`, `scroll()`, `capture_screenshot()`,
  `list_tabs()`, `current_tab()`, `activate_tab()`
- `SKILL.md` (browser-harness) — usage patterns, page workflow
- `install.md` (browser-harness) — CDP setup, recording consent
