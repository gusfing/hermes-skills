# Worked session: Hermes WebUI on Oracle Linux 9, reachable from iPhone

Concrete transcript of the class-level workflow in `SKILL.md`. Useful as a
reproduction recipe and as evidence of what the brief-vs-reality gap looks like.

## Environment

- Oracle Linux Server 9.8 (`ID=ol`, `ID_LIKE=fedora`) — firewalld, systemd,
  public NIC `enp0s6` plus `tailscale0`.
- Repo: `/home/opc/hermes-webui` (github.com/nesquena/hermes-webui).
- Interpreter: `/home/opc/.hermes/hermes-agent/venv/bin/python` (note: `venv`,
  NOT `.venv`).
- Tailnet `ks05460@`, host `instance-20260802-0122`, peer `iphone173`.

## Brief vs reality

| Brief said | Reality |
| --- | --- |
| Clone the repo | Already cloned at the cwd |
| Node.js app, `npm install` | Python: `server.py`, `bootstrap.py`, `requirements.txt` |
| Install Tailscale | Already installed at `/usr/bin/tailscale` and authenticated |
| Authenticate, may need auth key/URL | Already authed; iPhone already a tailnet peer |
| Try `tailscale serve --bg 8787` | Serve already active, proxying `/` -> `127.0.0.1:8787` |
| Set up auto-start | Unit `hermes-webui.service` already existed but `inactive dead` |

Net effect: the only genuinely new work was the password, and fixing three
latent defects the user did not know about.

## Defects found and fixed

1. **Broken autostart.** `/usr/local/bin/hermes-webui-server` had
   `exec /home/opc/.hermes/hermes-agent/.venv/bin/python ...` but only `venv`
   exists. The unit failed at every boot silently. Rewrote the wrapper.

2. **Port 8787 open to the public internet.** firewalld `public` zone listed
   `9377/tcp 8080/tcp 8000/tcp 8787/tcp` and the box has a public NIC. Since the
   unit binds `0.0.0.0`, this was a genuinely internet-exposed service.
   Remediation:
   ```bash
   sudo firewall-cmd --zone=trusted --add-interface=tailscale0 --permanent
   sudo firewall-cmd --zone=public  --remove-port=8787/tcp --permanent
   sudo firewall-cmd --reload
   ```
   `tailscale0` had no zone at all beforehand (`--get-zone-of-interface` -> `no zone`).
   Left 8000/8080/9377 open but flagged them to the user.

3. **Service ran as root.** Root-owned files had appeared under
   `/home/opc/.hermes/webui`: `.signing_key`, `.pbkdf2_key`, `.sessions.json`,
   `.login_attempts.json`, `sessions/_index.json`. Fixed with a
   `User=opc / Group=opc` drop-in plus `chown -R`.

## Auth wiring

`/etc/default/hermes-webui`, mode 600, read by the unit's `EnvironmentFile=`:

```
HERMES_WEBUI_PASSWORD=<24-char CSPRNG alnum>
HERMES_WEBUI_HOST=0.0.0.0
HERMES_WEBUI_PORT=8787
```

The repo documents these in `.env.example` (`HERMES_WEBUI_PASSWORD`,
`HERMES_WEBUI_HOST`). No `.env` existed; the EnvironmentFile route was chosen
over creating one.

### Login endpoint gotcha

The login route is **`POST /api/auth/login` with a JSON body**, found via
`grep -rn "login" api/routes.py` (see `api/routes.py:5434`). An initial guess of
a form POST to `/login` with a scraped CSRF token returned `404` for both the
correct and the wrong password — an ambiguous result that must not be read as
success. Correct probe:

```bash
curl -s -H 'Content-Type: application/json' -d '{"password":"..."}' \
  http://100.x.x.x:8787/api/auth/login
# good -> 200 {"ok": true}
# bad  -> 401 {"error": "Invalid password"}
```

Note there is also a passkey route at `/api/auth/passkey/login`.

## Pre-existing process conflict

`ss -lntp` showed `127.0.0.1:8787` held by a manually-launched
`python server.py` (PID 31941, ~1m uptime). `start.sh` refuses to double-start
by probing `/health` first, and would have reported "already running". The
orphan had to be killed before `systemctl start` could bind.

## Final verification (all observed, not assumed)

```
health via tailnet IP        200
health via ts.net HTTPS      200
GET /  (unauthenticated)     302 -> /login?next=/
POST login, correct pw       200
POST login, wrong pw         401
systemctl is-enabled         enabled  (hermes-webui + tailscaled)
process owner                opc
find state-dir -user root    (empty)
```

## Delivered to the user

- URL: `https://instance-20260802-0122.tail2dfc33.ts.net` (HTTPS hostname, not
  the `100.93.145.31` IP — real cert, no iOS TLS warning).
- Password: the generated 24-char string.
- iPhone steps: Tailscale app toggle ON, then enter URL + password in Hermex.
  Emphasised that a failed connection is almost always the VPN toggle, since
  the service is now tailnet-only by design.
