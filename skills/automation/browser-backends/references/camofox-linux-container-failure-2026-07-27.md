# Camofox Linux container failure signature — 2026-07-27

## Observed failure
- Camofox server starts and answers `/health`
- Browser launch fails with containerized-Linux error pattern:\n  - `libgtk-3.so.0: cannot open shared object file: No such file or directory`
  - `Sandbox: CanCreateUserNamespace() clone() failure: EPERM`
  - `Running Camoufox as root in a regular user's session is not supported. ($HOME is /opt/data which is owned by hermes.)`
  - `Version information not found at /root/.cache/camoufox/version.json. Please run camoufox fetch to install.`

### Fast probes that show this root cause
```bash
curl -s http://127.0.0.1:9377/health          # may return {"ok":true,"browserRunning":false,...}
find / -name 'libgtk-3.so.0' 2>/dev/null       # empty before dependency install
unshare --user true                             # EPERM on disallowed unprivileged user namespaces
ps eww -p 10                                   # shows whether root has HOME=/root or HOME inherited from non-root home
```

## Working repair path when apt/root is available

1. Install missing dependencies. On Debian Trixie, package names may use `t64` suffixes.
2. Use a root-owned Camoufox cache and set `HOME=/root` when starting the Camofox server.
3. Run `HOME=/root npx -y camoufox-js fetch` so `/root/.cache/camofox/version.json` and binaries are created.
4. Start the server with `HOME=/root CAMOFOX_PORT=9377 node .../camofox-browser/server.js`.
5. If startup reports `port in use`, kill old Node servers first: `pkill -f 'node server.js' || true`.

After these steps, `/health` should return `"browserConnected": true, "browserRunning": true`.

## Working fallback when repair is not possible

Chrome CDP at `http://127.0.0.1:9222` may already be running. Switching browser tools to that backend through `/browser connect http://127.0.0.1:9222` can restore automation.

## Lesson

Package presence ≠ launchability. Health showing `browserRunning:false` often means Camofox is up but launch/logic conditions are wrong. In restricted containers this needs either Chrome CDP fallback or an environment with apt/root access.
