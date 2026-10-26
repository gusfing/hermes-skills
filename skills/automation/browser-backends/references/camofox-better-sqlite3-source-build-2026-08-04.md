# Camofox `better-sqlite3` source-build repair on Oracle Linux 9 aarch64

## Context

- Host: Oracle Linux 9 aarch64
- glibc: 2.34
- Package: `@askjo/camofox-browser`
- Blocker: `/lib64/libm.so.6: version 'GLIBC_2.38' not found (required by .../better-sqlite3/prebuilds/linux-arm64.node)`

## Verified repair

```bash
sudo dnf install -y sqlite-devel gcc gcc-c++ make python3-devel
sudo npm install -g node-gyp
cd /home/opc/.local/lib/node_modules/@askjo/camofox-browser/node_modules/better-sqlite3
npm run build-release
cp build/Release/better_sqlite3.node prebuilds/linux-arm64.node
node -e "require('/home/opc/.local/lib/node_modules/@askjo/camofox-browser/node_modules/better-sqlite3'); console.log('ok')"
```

Result:
- `node -e require(...)` prints `ok`
- Camofox server starts on `9377`
- `/` returns `{"ok":true,...,"browserConnected":true,"browserRunning":true}`
- `browser pre-warmed` appears in logs

## Important limitation

Even with `better-sqlite3` fixed, this Camofox build does **not** expose Chrome-style CDP endpoints. `browser-harness` cannot attach to it because it requires `/json/list`, `/json/version`, and WebSocket debugger URLs that Camofox does not provide in this build.

## Implication for automation

- Camofox is now runnable on this host class after the source-build patch.
- For `browser-harness`-style automation, prefer direct Chrome CDP instead of Camofox on this host.
- For Camofox-only workflows, use its own session API (`/sessions/:userId/cookies`, etc.).
