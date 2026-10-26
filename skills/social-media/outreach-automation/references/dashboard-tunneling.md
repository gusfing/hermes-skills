# Dashboard tunneling

## Problem
The outreach dashboard often runs inside a container or VM where dashboard port `3001` is not directly reachable from the user's phone or external browser.

## Options
1. **Direct IP/port** — first check from inside the container whether `curl http://127.0.0.1:3001` works. Then test external reachability with the public IP.
2. **localtunnel** — install locally, not globally. Use ESM/CJS-compatible invocation. Do not assume `.on()`; the module may export a plain async factory or default export.
3. **localhost.run** — SSH reverse tunnel with `ssh -o StrictHostKeyChecking=no -R 80:localhost:3001 nokey@localhost.run`. Remote port `80` is more likely to bind than `3001`.
4. **serveo.net** — same shape as `localhost.run`: `ssh -o StrictHostKeyChecking=no -R 80:localhost:3001 serveo.net`.
5. **cloudflared quick tunnel** — `cloudflared tunnel --no-autoupdate --url http://localhost:PORT`. Needs no Cloudflare account and returns a random `*.trycloudflare.com` hostname. This is the fastest path when OCI-style firewalls expose only 80/443 and block raw high ports.

## Pitfalls
- Do not block the dashboard route handler on tunnel startup. Start tunnel in a detached process; return success to browser immediately.
- `localtunnel` success does not mean external reachability. Verify with an external `curl` to the tunnel URL.
- `headless false` in container without X server crashes Playwright. Use `headless: true` when no display is available.
- If the tunnel drops, the dashboard URL may return 502. Stop retrying the same URL; restart tunnel and validate.

## cloudflared quick-tunnel specifics (measured 2026-09-29)

**`grep -oP` for a URL does not capture a trailing slash.** Building the
user-facing URL as `"${URL}vnc.html?..."` yields
`https://x.trycloudflare.comvnc.html?...` — host and path fused into one
token. It reads like a valid hostname in a log line or a notification, and it
fails at request time, long after the script that produced it has exited.
Always write `${URL}/path` and `curl` the exact string before handing it over.

**One tunnel per port, or it is a race.** Restarting without reaping the old
process leaves two `cloudflared` instances bound to the same upstream port, and
which one owns the hostname is unpredictable. Enumerate first
(`pgrep -af "localhost:PORT" | grep -v "bash -c"`), kill the stale PID, then
confirm exactly one remains.

**`completed normally` on a launcher is not tunnel death.** A script that
spawns the tunnel and prints a URL then exits is reported as a completed
background job while the tunnel keeps serving. Judge liveness by the URL, not
the exit status of its parent:

```
dead hostname  -> 530
live, no auth  -> 200
live, behind basic auth -> 401   (this is success)
```

**Hostname changes on every restart.** Never quote a stored quick-tunnel URL
from earlier in the conversation; re-read it from the log and confirm it
responds before presenting it.

**`pkill -f` inside the tunnel script matches itself.** `pkill -f "cloudflared
tunnel --url http://localhost:6082"` appears verbatim in the script's own
command line and can kill the caller. Bracket a character:
`"localhost:608[2]"`.

**`systemctl start` on a root-owned unit** can fail with "Interactive
authentication required" from a non-root shell even when passwordless sudo
works. Launch the script directly rather than reporting the service as
unavailable.

## Gateway credential recovery

An htpasswd file stores a one-way `apr1` hash, so **the plaintext password
cannot be read back** — by design. When a user asks for a tunnel password and
no plaintext copy exists anywhere, recovery is impossible; do not go hunting in
shell history expecting to find it. Reset and re-verify all three cases before
handing over a new one:

```
real credentials -> 200
wrong password   -> 401
no password      -> 401
```

Then `nginx -t` to confirm the file is still parseable, and keep the file
`root:nginx 0640` — nginx workers are not root, and a 500 means nginx cannot
read the file rather than that the upstream is broken.
