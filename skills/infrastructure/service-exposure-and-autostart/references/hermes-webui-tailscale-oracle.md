# Hermes WebUI + Tailscale on Oracle Linux 9 — worked session

## What was true on this box

- OS: Oracle Linux 9.8 (aarch64), user `opc`.
- Hermes Agent installed at `/home/opc/.hermes/hermes-agent`.
- Hermes CLI venv Python at `/home/opc/.hermes/hermes-agent/venv/bin/python`.
- hermes-webui repo already cloned at `/home/opc/hermes-webui`.
- Tailscale installed via CentOS 9 repo and already authenticated.
- Tailscale Serve already configured and working.
- Existing orphan server already listening on `127.0.0.1:8787` before starting.

## What actually ran

1. Recon showed `hermes-webui` was Python, not Node; no `npm install` needed.
2. Stopped orphan `server.py` by PID before starting anything else.
3. Generated password with `openssl rand -hex 24`.
4. Started WebUI via `./ctl.sh start` with env vars:
   - `HERMES_WEBUI_AGENT_DIR=/home/opc/.hermes/hermes-agent`
   - `HERMES_WEBUI_PYTHON=/home/opc/.hermes/hermes-agent/verv/bin/python`
   - `HERMES_WEBUI_PASSWORD=<hex>`
   - `HERMES_WEBUI_HOST=127.0.0.1`
   - `HERMES_WEBUI_PORT=8787`
5. Confirmed auth: `curl /api/sessions` returned `401`.
6. Tailscale Serve already proxying `/` to `http://127.0.0.1:8787`.
7. Created systemd user unit at `~/.config/systemd/user/hermes-webui.service`
   with the same env vars; enabled and verified `is-enabled`.
8. Verified:
   - `http://$(tailscale ip -4):8787/health` → 000 (Serve intercepts HTTP)
   - `https://<host>.tail2dfc33.ts.net/health` → 200
   - `/api/sessions` → 401
9. When `ctl.sh start` conflicts with an existing systemd unit, use
   `systemctl --user restart hermes-webui.service` directly; do not fight ctl.sh
   with HERMES_WEBUI_CTL_ALLOW_SYSTEMD_CONFLICT.
10. If exposing on the tailnet IP as well as Serve, set
    `HERMES_WEBUI_COOKIE_NAME=hermes_session_<port>` and
    `HERMES_WEBUI_CSP_CONNECT_EXTRA` to include the tailnet IP/port so
    Safari connects cleanly.

## Notable lessons

- Do not re-bind the app to `0.0.0.0` when Tailscale Serve is available; keep
  it on `127.0.0.1` and let Serve handle TLS + hostname.
- Orphan server processes cause false positives on `/health`; always kill them
  before enabling a new unit.
- `/health` alone does not prove auth; `/api/sessions` is the correct auth
  probe for `hermes-webui`.
- `/api/auth/login` can return 200 while every subsequent request returns 401 —
  that means the client is not storing the session cookie. On iOS, check for
  Private Browsing mode or strict cookie blocking before debugging the server.
- When the client-side login appears broken on mobile, test the full cookie
  round-trip from the server side first: login with `-c`, then a follow-up
  request with `-b` to the session endpoint. If that works server-side, the
  issue is client storage, not auth.

## Delivered values

- URL: `https://instance-20260802-0122.tail2dfc33.ts.net`
- Password: saved in systemd unit env, not reproduced here.
