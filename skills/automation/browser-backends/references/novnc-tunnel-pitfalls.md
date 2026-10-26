# noVNC quick-tunnel pitfalls (verified 2026-09-29)

Applies to `cloudflared tunnel --url` + `websockify` + nginx basic-auth, the
shape used to hand a human a login wall on a headless box. See also the
`browser-remote-desktop-novnc` skill for the build recipe (not
curator-managed).

## Two tunnels on one port makes the URL a coin flip

A stale `cloudflared` was still bound to `localhost:6082` after a restart.
Two quick tunnels then competed for the same port, so *which* hostname
actually served was a race.

Symptom seen: the old URL returned `530`, the new one returned `401`
(correct — auth working), and `pgrep` returned two pids.

```bash
pgrep -af 'cloudflared tunnel --url http://localhost:6082'   # count > 1 = broken
```

Always check the count before handing the user a link. Kill the stale pid and
re-read the surviving process' log for its real hostname — a quick tunnel
hostname changes on every start, so the URL in an old log line or an old
message is dead. Never hardcode it into docs.

## The missing-slash URL that looks fine in a terminal

A wrapper captured the hostname with `grep -oE 'https://[a-z-]+\.trycloudflare\.com'`
and then printed:

```sh
echo "${URL}vnc.html"    # -> https://xxx.trycloudflare.comvnc.html
```

`grep -oE` on that pattern captures **no trailing slash**, so concatenation
produces a broken URL. In a terminal it reads as plausible, and the user only
finds out on click. Build it explicitly:

```sh
echo "${URL}/vnc.html?autoconnect=1&resize=scale&path=websockify"
```

The `?autoconnect=1&resize=scale&path=websockify` query is what makes the page
connect without the user clicking through the noVNC control panel.

## nginx auth must not depend on the Host header

Put `auth_basic` on a **dedicated port** with its own `server {}` block, not on
a shared vhost selected by `server_name`. A quick tunnel sends an arbitrary
`Host`, so any `default_server` catch-all can serve the wrong block and bypass
(or wrongly enforce) the gate. Verify from outside the tunnel: no credentials
-> 401, wrong credentials -> 401, real credentials -> 200.

## htpasswd hashes are one-way — plan for a reset, not a recovery

An `apr1` htpasswd entry cannot be read back. If the password is lost, the
only fix is to write a new one. Check for a plaintext copy in
`~/.bash_history`, systemd drop-ins, or stray files before concluding the
password is unrecoverable — but expect to reset, and tell the user a reset
happened rather than implying you recovered the old value.

```sh
sudo htpasswd -B -c /etc/nginx/.vnc-htpasswd vnc    # 640, root:nginx
```

`-B` (bcrypt) over apr1 when the consumer supports it.

## The unit needs sudo and a foreground process

`systemctl start vnc-tunnel` requires interactive auth. Run the script
directly as a background process. The service script must also end in
something blocking (e.g. `tail -f /dev/null`) or `Type=simple` restarts it
and `KillMode=control-group` takes websockify down with it -> 502.

## Login state, not a listening socket

A bound 5901/6081/6082 proves nothing about usability. Screenshot the
framebuffer and look at it (`ffmpeg -f x11grab -video_size WxH -i :N
-frames:v 1 -update 1 out.png` works where imagemagick is absent). The
framebuffer can be up while the browser inside is showing a login modal, or
the page can be blank because client-side JS has not run yet — screenshot
twice, once after a delay, before declaring it broken.
