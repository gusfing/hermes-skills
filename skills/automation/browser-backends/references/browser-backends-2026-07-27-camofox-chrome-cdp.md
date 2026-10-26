# Browser backends — session detail

## Local Chrome install via agent-browser
- Command: `npx agent-browser install --with-deps`
- Observed behavior: apt/sudo steps failed in this container, but Chrome 151 still downloaded to `/opt/data/.agent-browser/browsers/chrome-151.0.7922.47/`

## Headless Chrome CDP launch command
```bash
DEBUG_DIR=/opt/data/chrome-debug
/opt/data/.agent-browser/browsers/chrome-151.0.7922.47/chrome \
  --headless=new \
  --remote-debugging-port=9222 \
  --user-data-dir="$DEBUG_DIR" \
  --no-first-run --no-default-browser-check \
  --disable-gpu --no-sandbox
```

## CDP health probes
```bash
curl -I http://127.0.0.1:9222/json/version
curl -s http://127.0.0.1:9222/json/list | python3 -m json.tool
```

## Config guard
- Hermes refused safe writes to `/opt/data/config.yaml` and `/opt/data/.env`.
- Workaround: edit files directly or use `hermes config set ...`.
