---
name: browser-remote-desktop-novnc
description: Expose a headless Linux desktop for manual logins via noVNC.
---

# Remote Desktop via noVNC (no extra ports, no VNC client)

Use when a site needs a human to type a password (login walls, 2FA, OAuth) and
the box has no physical screen. Gives a normal `https://` URL that works in any
browser on any OS.

## Why this shape

- **Cloudflare quick tunnel, not a DNS record.** A record needs an API token;
  `cloudflared tunnel --url` needs nothing and returns a random public hostname.
- **Auth in nginx, not in the tunnel.** A quick tunnel is unauthenticated. Put
  basic auth on a dedicated port so the gate cannot be bypassed by Host-header
  tricks, and never expose the websockify port itself.
- **Bind raw VNC and websockify to loopback.** Only nginx should reach them.

## Steps

1. Packages. Oracle Linux 9 keeps these in `codex`/`ol9_codeready`, not the
   default repos: `sudo dnf install -y tigervnc-server httpd-tools`.
   noVNC is not packaged — `git clone --depth 1
   https://github.com/novnc/noVNC.git /usr/share/novnc`.
2. `Xvnc` is the X server AND the VNC server in one process. Binary is
   `/usr/bin/Xvnc`, **not** `Xtigervnc`. TigerVNC rejects x11vnc's `-forever`
   and `-shared`; use `-localhost -SecurityTypes None`.
3. `python -m websockify --web /usr/share/novnc 127.0.0.1:6081 localhost:5901`
4. nginx on a dedicated port, `auth_basic` against an htpasswd file that is
   `root:nginx 0640` — nginx workers are not root, and a 500 here means nginx
   cannot read the password file, not that the upstream is broken.
5. `cloudflared tunnel --no-autoupdate --url http://localhost:6082`

## Verify before telling the user it works

From OUTSIDE, over the tunnel URL, all three:

- no credentials -> **401**
- wrong credentials -> **401**
- real credentials -> **200**

Then screenshot the framebuffer and look at it. Do not report "desktop is up"
from a listening socket alone. `ffmpeg -f x11grab -video_size WxH -i :N
-frames:v 1 -update 1 out.png` works where `import`/`xwd`/`imagemagick` are
absent (this box has no imagemagick and it is not installable).

## Pitfalls that cost real time here

- **systemd `Type=simple` needs a foreground process.** A setup script that
  prints status and exits makes the unit look dead; systemd restarts it, and
  `KillMode=control-group` kills websockify -> 502. End the script with
  `tail -f /dev/null`.
- **GNOME keyring pops a modal on first Chrome run** and blocks the page
  forever. Launch Chrome with `--password-store=basic --use-mock-keychain`.
- **Never `pkill -f "google-chrome"`** in a command that itself contains that
  string — it matches its own shell and kills the caller. Use a bracket
  pattern: `pkill -f "li-chrome[-]profile"`.
- Run scripts with the Hermes venv python if they need `playwright`/
  `websockify`; system python3 lacks those modules.
- A quick-tunnel hostname changes on every restart. Persist the URL or have the
  user re-read it; do not hardcode it into docs and call it stable.

## Files this created

`/home/opc/bin/remote-desktop`, `/home/opc/bin/vnc-tunnel`,
`/etc/nginx/conf.d/vnc-tunnel.conf`, `/etc/systemd/system/remote-desktop.service`,
`/etc/nginx/.vnc-htpasswd` (`root:nginx 0640`).
