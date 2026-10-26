# browser-harness on Oracle Linux 9 aarch64

## Install (current verified path)

```bash
uv tools install browser-harness --python python3.12
# upgrade if already installed:
uv tools upgrade browser-harness --python python3.12
```

This lands the CLI at `~/.local/bin/browser-harness` and the package under
`~/.local/share/uv/tools/browser-harness/`. After install, read three files:
1. `install.md` — setup steps, CDP wiring, recording consent
2. `SKILL.md` — normal usage patterns
3. `helpers.py` — the actual functions (location below)

**helpers.py location:**
`~/.local/share/uv/tools/browser-harness/lib/python3.12/site-packages/browser_harness/helpers.py`
(or `lib64/` on some installs). Always read this — it is where the functions live.

**Gotcha:** `from browser_harness.helpers import page_info` fails in standalone
Python scripts with `ModuleNotFoundError`. Drive browser-harness through the CLI:
`browser-harness <<'PY' ... PY`.

## Chrome install

Oracle Linux 9 lacks chromium/google-chrome in default repos. Add Google's repo:

```bash
cat <<'EOF' | sudo tee /etc/yum.repos.d/google-chrome.repo
[google-chrome]
name=google-chrome
baseurl=https://dl.google.com/linux/chrome/rpm/stable/aarch64
enabled=1
gpgcheck=1
gpgkey=https://dl.google.com/linux/linux_signing_key.pub
EOF
sudo dnf install -y google-chrome-stable
```

Verified version: `Google Chrome 151.0.7922.71` on aarch64.

## Launch Chrome for harness

Chrome on a VNC desktop needs DISPLAY, XAUTHORITY, DBUS_SESSION_BUS_ADDRESS,
and HOME set. Use the included script:

```bash
python3.12 /home/opc/.hermes/skills/automation/browser-backends/scripts/launch-chrome-cdp.py
```

Or launch manually:

```bash
export DISPLAY=:1 XAUTHORITY=/home/opc/.Xauthority \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus HOME=/home/opc
google-chrome \
  --remote-debugging-port=9222 \
  --remote-debugging-address=0.0.0.0 \
  --user-data-dir=/home/opc/chrome-vnc-profile \
  --no-first-run --no-default-browser-check \
  --disable-gpu --disable-dev-shm-usage \
  --no-sandbox --disable-software-rasterizer \
  > /tmp/chrome-vnc.log 2>&1 &
sleep 5
curl -s http://127.0.0.1:9222/json/version
```

**Critical pitfall — Chrome keeps dying in background shells:**
Launching Chrome with `&` or `background=true` in terminal often kills the
process when the shell exits. The fix is one of:
1. Use `launch-chrome-cdp.py` which uses `subprocess.Popen` with proper env
2. Launch via `computer_use` on the VNC desktop GUI
3. Keep the launch in a persistent process tracked by Hermes
4. Use `setsid ... &` with proper process group detachment

**Scoped profile pitfall:** headless Chrome with `--headless=new` creates a
scoped profile under `/home/opc/.config/google-chrome-headless/scoped_dir...`
that browser-harness's autodetect misses. Always set
`BU_CDP_URL=http://127.0.0.1:9222` explicitly.

## Connect browser-harness

```bash
BU_CDP_URL=http://127.0.0.1:9222 browser-harness <<'PY'
print(page_info())
PY
```

`--doctor` may report `chrome-not-running` even when Chrome is up; setting
`BU_CDP_URL` explicitly resolves that.

## Switch to an existing non-internal tab

```bash
BU_CDP_URL=http://127.0.0.1:9222 browser-harness <<'PY'
for t in list_tabs(include_chrome=False):
    if 'github.com/browser-use/browser-harness' in t.get('url',''):
        switch_tab(t['targetId'])
        break
print(page_info())
PY
```

## Demo navigation

```bash
browser-harness <<'PY'
new_tab('https://github.com/browser-use/browser-harness')
wait_for_load()
print(page_info()['url'])
PY
```

## Support files

- `scripts/launch-chrome-cdp.py` — reliable Chrome CDP launcher using
  subprocess.Popen with correct DISPLAY/XAUTHORITY/DBUS env vars. Handles
  stale-process cleanup and 30s CDP readiness polling.
- `references/browser-harness-helpers-reference.md` — full function reference
  for helpers.py (538 lines): all function signatures, IPC mechanism, tab
  management patterns.
