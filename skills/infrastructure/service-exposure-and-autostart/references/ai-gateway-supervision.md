# Supervising a Local AI Gateway (9router class)

Worked example: 9router serving port **20128** — which is also the Hermes model
provider — running in a raw terminal with no supervision at all.

## The self-referential failure mode

Check *what depends on the service* before supervising it:

```bash
grep -rn -A6 "<port>" ~/.hermes/config.yaml
# provider custom:
#   - name: Local (localhost:20128)
#     base_url: http://localhost:20128/v1
#     key_env: HERMES_CUSTOM_LOCALHOST_20128_API_KEY
```

When the unsupervised service is the agent's own inference provider, its death is not
a partial outage — the agent loses the ability to think, mid-task, with no way to
recover on its own. This raises the bar for the audit: check `ps` for a tty parent
(`pts/N`) and no `~/.config/systemd/user/` unit, even though the service is up and
answering requests right now. "Working" and "always working" are different states and
only the second was asked for.

## Copy the sibling unit

A related tool was already supervised, so read it and match it exactly rather than
authoring fresh:

```bash
ls ~/.config/systemd/user/ | grep -i <tool>
# cc.9remote.agent.service   <- already enabled, working
```

The copied conventions that mattered: absolute node path
(`/home/opc/.hermes/node/bin/node`), the real CLI entrypoint rather than a `PATH`
lookup, `--tray --skip-update` flags quoted individually, and
`StandardOutput=append:<state-dir>/logs/autostart.log` instead of the journal.

Add `--no-browser` on a headless host — the tray mode otherwise expects a desktop.

**Port handover order matters:** kill the unsupervised PID first, confirm the port is
free, *then* `systemctl --user enable --now`. Both processes otherwise contend for
20128 and the unit crash-loops against a listener you think you removed.

## Verification: only a real inference call counts

The cheap checks are individually misleading, and this session hit both:

| Probe | Result | Meaning |
|-------|--------|---------|
| `GET /health` | **404** | Path does not exist. Not a fault, not a signal either way. |
| `GET /v1/models` | 200 **unauthenticated** | Proves the process serves HTTP. Says nothing about whether inference works. |
| `POST /v1/chat/completions` no key | `Missing API key` | Confirms auth is enforced — a *negative* result, easy to misread as broken. |

The only check that proves the agent can still think is a real completion with the real
key, read from the same env var the config references:

```bash
K="${HERMES_CUSTOM_LOCALHOST_20128_API_KEY}"
curl -s -m 90 http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" -H "Authorization: Bearer $K" \
  -d '{"model":"claude-opencode","messages":[{"role":"user","content":"Reply: PONG"}],"max_tokens":10}'
# -> {"choices":[{"message":{"content":"P"}...}],"usage":{...}}   truncated is fine
```

Then prove supervision actually works, not just that the unit starts:

```bash
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user is-active 9router.service     # active
systemctl --user is-enabled 9router.service    # enabled  <- survives reboot
MAIN=$(systemctl --user show 9router.service -p MainPID --value)
kill -9 $MAIN; sleep 25
systemctl --user show 9router.service -p MainPID --value   # DIFFERENT pid
curl -s -m 10 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:<port>/v1/models
```

`XDG_RUNTIME_DIR` is required for `systemctl --user` over SSH on some systems;
`--user is-system-running` reporting `degraded` is a red herring — check
`--failed` for the actual cause rather than assuming the manager is unusable.

### System vs. user units: install into the right one

Deciding between `systemctl` and `systemctl --user` is not cosmetic. Installing a
user-scoped service as a *system* unit silently puts it under root's control, so it
starts before the login session the `Linger=yes` guarantee depends on, and
`systemctl --user is-enabled` will disagree with `systemctl is-enabled` about whether
you set it up at all.

The evidence for which scope the user actually uses is the parent PID:

```bash
ps -o pid,ppid,args -p <pid-of-working-sibling>
# 2448  1  /usr/lib/systemd/systemd --user   -> user scope; match it
```

Copy the sibling's scope, not just its contents. A service that must be reachable
before login belongs in a *system* unit instead — but check what the already-working
neighbour does before assuming either.

Confirm the scope you actually installed into:

```bash
systemctl --user is-enabled <svc>   # for a user unit
systemctl is-enabled <svc>          # for a system unit (needs sudo)
ls -la /etc/systemd/system/<svc> ~/.config/systemd/user/<svc>   # exactly one exists
```

## Flag the bind address, then let the user choose

9router binds `0.0.0.0` and logs its own warning. Report reachability and the
consequence plainly, then offer the option — do not silently add `--host 127.0.0.1`
when another instance on the same VCN may legitimately call it:

> It binds `0.0.0.0`, reachable at `http://10.0.2.22:20128`. The OCI security list only
> allows 80/443 inbound, so it is not internet-reachable, but anything on the VCN could
> reach it. Loopback-only is safe if only Hermes consumes it.

## Background-process exit 124 is not an outage

A `timeout 120 <cmd>` scratch instance fires a completion notification with exit **124**
on expiry. That is `timeout` working as designed. Before reporting any impact, check
which process it actually was:

```bash
systemctl is-active <the-real-unit>
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:<port>/<health-path>
```

If the real service is active and answering, the notification is noise — say so in one
line and move on. Do not re-verify the whole stack or re-narrate the earlier work.
