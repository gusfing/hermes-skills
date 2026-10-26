---
name: tailnet-service-exposure
description: Expose a self-hosted service over Tailscale, safely.
---

# Exposing a self-hosted service over Tailscale

Class of task: "install/run app X on this box and let me reach it from my phone
(or another device) over Tailscale, with a password, surviving reboots."

Covers: Tailscale Serve vs raw tailnet-IP bind, auth verification, systemd
autostart, firewall scoping, non-root service ownership.

## Step 0 — Reconcile the brief with the machine BEFORE acting

User briefs for this task class are routinely stale or wrong. They are written
from memory or from a README skimmed months ago. Always run a reconnaissance
pass first and report every mismatch in your final reply.

Check, in one batched turn:

```bash
cd <repo> && git remote -v && ls          # already cloned? which remote?
cat /etc/os-release | head -5             # distro family drives install cmds
which node npm python3 tailscale          # what is actually installed
tailscale status; tailscale ip -4         # already authed? peers present?
tailscale serve status                    # already proxying?
ss -lntp | grep <port>                    # already listening? which PID?
systemctl list-units --all | grep -i <name>   # dormant unit already exists?
```

Mismatches seen in practice, all in a single session:
- "Clone this repo" — it was already cloned in the cwd.
- "It's a Node.js app" — it was Python (`server.py`, `requirements.txt`); no
  `npm install` existed to run.
- "Install Tailscale" — installed AND already authenticated; no auth URL needed.
- "Try tailscale serve" — Serve was already configured and working.
- A `systemd` unit already existed but was `inactive dead` from a latent bug.

Do not perform a step whose precondition is already satisfied, and never invent
an install you did not run. State the corrections plainly to the user — they
are usually the most valuable part of the reply.

## Step 1 — Auth BEFORE reachability

Never widen network exposure before confirming the auth gate is live. Order:
set the password, restart, prove auth works, then open the network path.

Generate the secret with a CSPRNG, not a hand-typed string:

```bash
python3 -c "import secrets,string; a=string.ascii_letters+string.digits; print(''.join(secrets.choice(a) for _ in range(24)))"
```

Store it in the systemd `EnvironmentFile` (e.g. `/etc/default/<svc>`) and
`chmod 600` it. Prefer that over a repo `.env`, which is world-readable and
easy to commit by accident.

## Step 2 — Prove auth with the REAL endpoint, both directions

Do not assume the login route shape. Guessing a form POST at `/login` returned
`404` for both a correct and a wrong password — which looks like "auth is
broken" but actually meant "wrong endpoint", and a lazier check could have been
misread as success. Find the route in the source first:

```bash
grep -rn "login" api/*.py server.py | grep -i "path\|route\|== \"/"
```

Then test BOTH directions. A correct-password 200 alone proves nothing; you
need the wrong password to be rejected:

```bash
curl -s -o /dev/null -w "good=%{http_code}\n" -H 'Content-Type: application/json' \
  -d '{"password":"<real>"}' $URL/api/auth/login    # expect 200
curl -s -o /dev/null -w "bad=%{http_code}\n"  -H 'Content-Type: application/json' \
  -d '{"password":"nope"}'   $URL/api/auth/login    # expect 401
curl -s -o /dev/null -w "root=%{http_code}\n" $URL/               # expect 302 -> /login
```

If you cannot get a definitive 401 on a bad password, treat auth as NOT proven
and do not expand exposure. Fail closed.

## Step 3 — Reachability: Serve first, bind second

Preferred, because it yields a real cert (no TLS warnings on iOS) and a stable
hostname:

```bash
tailscale serve --bg <port>
tailscale serve status     # -> https://<host>.<tailnet>.ts.net  proxy 127.0.0.1:<port>
```

Only if Serve is disabled on the tailnet, fall back to binding `0.0.0.0` — and
only after Step 2 passed. Give the user the HTTPS hostname, not the 100.x IP;
the IP works but produces cert warnings.

## Step 4 — Firewall: the step nobody asks for

Binding `0.0.0.0` on a cloud VM (Oracle Cloud, EC2, GCE, any box with a public
NIC) exposes the port to the entire internet, not just the tailnet. Always
audit and scope it:

```bash
sudo firewall-cmd --list-all                              # what is public?
sudo firewall-cmd --zone=trusted --add-interface=tailscale0 --permanent
sudo firewall-cmd --zone=public  --remove-port=<port>/tcp --permanent
sudo firewall-cmd --reload
```

Report any OTHER unexpected public ports you find while you are in there;
offer to close them rather than closing them unasked.

## Step 5 — Autostart, and run as a human user

`After=/Wants=network-online.target tailscaled.service` so the service does not
race the tunnel. Then verify `systemctl is-enabled` — "it is running right now"
is not evidence it survives a reboot.

Never let the unit run as root by default. A root-run service silently writes
root-owned signing keys and session databases into the user's `~`, which breaks
every later non-root run. Fix with a drop-in and repair the damage:

```bash
sudo mkdir -p /etc/systemd/system/<svc>.service.d
printf '[Service]\nUser=%s\nGroup=%s\n' opc opc | sudo tee /etc/systemd/system/<svc>.service.d/override.conf
sudo chown -R opc:opc <state-dir>
sudo systemctl daemon-reload && sudo systemctl restart <svc>
ps -o user,cmd -C python | grep server.py          # confirm the new user
find <state-dir> -user root | head                 # expect empty
```

## Pitfalls

- A dead unit whose `ExecStart` wrapper points at a venv that does not exist
  (`.venv` vs `venv`) fails silently at boot. `ls` the interpreter path in any
  wrapper script before trusting the unit.
- An orphaned manually-started process already holding the port makes the new
  unit fail to bind while `/health` still answers 200 from the old process —
  looks like success. Kill the orphan by PID, then start the unit, then confirm
  the listening PID is the unit's.
- Don't hand back the tailnet IP as the primary URL when Serve is available.
- `find <state-dir> -user root` is the cheap check that catches the root-run
  class of bug; run it after every service restart during setup.

## Final reply shape for this task class

Lead with corrections to the brief, then what you actually changed, then what
you VERIFIED (with the observed codes, not adjectives), then the user's
details: exact URL, password, and remaining device-side steps. Keep any
security finding (public port, root ownership) visible near the top — it is
what the user most needs and least expects.

See `references/hermes-webui-tailscale-oracle.md` for a full worked session.
