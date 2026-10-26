---
name: node-native-addon-abi-mismatch-oracle-linux
description: Node.js native addon (.node file) compiled for one Node ABI fails on another — diagnosis and rebuild on Oracle Linux dual-Node environments.
---

# Node.js Native Addon ABI Mismatch on Dual-Node Oracle Linux

## Context

Oracle Linux 9 servers running Hermes Agent often have two Node.js binaries installed:

- **System Node:** `/usr/bin/node` — Oracle's packaged version (e.g., v20.20.2, ABI 115)
- **Hermes Node:** `/home/opc/.hermes/node/bin/node` — Hermes's bundled version (e.g., v22.23.2, ABI 127)

When a native addon (`.node` file, e.g., better-sqlite3, bcrypt, sharp) is compiled against one Node version, it carries that ABI version (`NODE_MODULE_VERSION`). Loading it from the other Node binary fails:

```
Error: The module '/path/to/addon.node' was compiled against a different Node.js version using
NODE_MODULE_VERSION 127. This version of Node.js requires NODE_MODULE_VERSION 115.
Please try re-compiling or re-installing the module.
```

## Diagnosis

### 1. Identify which Node the app process uses

Check the running process environment:

```bash
cat /proc/<PID>/environ | tr '\0' '\n' | grep -E "NODE_PATH|PATH|HOME"
```

The `PATH` variable reveals which `node` binary is found first. `NODE_PATH` controls where `require()` searches for native modules.

### 2. Check the .node file's ABI version

```bash
node -e "
const fs = require('fs');
const buf = fs.readFileSync('/path/to/addon.node');
// NODE_MODULE_VERSION is at offset 8 in the magic header (2 bytes, little-endian)
const abi = buf.readUInt16LE(8);
console.log('ABI version:', abi, '(115=Node20, 127=Node22)');
"
```

### 3. Check which Node runs the app

For systemd services:

```bash
cat /etc/systemd/system/<service>.service | grep ExecStart
```

- `/usr/bin/node` → system Node (ABI 115 on Oracle Linux 9)
- `/home/opc/.hermes/node/bin/node` → Hermes Node (ABI 127)

## Fix: Rebuild the native addon for the correct Node version

### Option A — npm rebuild (when npm's Node matches the target)

```bash
cd /path/to/module
npm rebuild better-sqlite3 --build-from-source
```

**Caveat:** npm uses its own bundled node-gyp tied to the npm binary's Node version. If npm is from Hermes Node (v22) but the app runs on system Node (v20), `npm rebuild` produces ABI 127 binaries — wrong for the app.

### Option B — system node-gyp directly (reliable, recommended)

```bash
# Find system node-gyp
NODE_GYP=$(find /usr/lib/node_modules/npm/bin -name node-gyp -type f | head -1)

# Rebuild for system Node (v20, ABI 115)
cd /path/to/module
bash $NODE_GYP rebuild --release --target=20.20.2 --arch=arm64 --dist-url=https://nodejs.org/dist
```

Key points:
- Use `bash` to run node-gyp (it's a shell script, not directly loadable by Node)
- `--target` must match the app's Node version exactly
- `--arch=arm64` for Oracle Linux ARM instances
- `--dist-url=https://nodejs.org/dist` ensures correct headers

### For Hermes Node (v22, ABI 127)

```bash
cd /path/to/module
/home/opc/.hermes/node/bin/node /home/opc/.hermes/node/lib/node_modules/npm/bin/node-gyp-bin/node-gyp rebuild --release --target=22.23.2 --arch=arm64
```

## Prevention

### Symlink the correct native addon into the app's node_modules

If the app's `node_modules` lacks the native addon but the runtime directory has it, symlink:

```bash
ln -sf /path/to/runtime/node_modules/better-sqlite3 /path/to/app/node_modules/better-sqlite3
```

### Set NODE_PATH consistently in systemd service

```ini
[Service]
Environment=NODE_PATH=/path/to/runtime/node_modules:/path/to/app/node_modules
```

## Example: better-sqlite3 on 9router (this session)

**Problem:** 9router runs on system Node (v20, ABI 115) but better-sqlite3 was compiled for Hermes Node (v22, ABI 127). All API endpoints returned `[DB] No SQLite driver available (bun/better/node/sql.js all failed)`.

**Diagnosis:** `NODE_PATH` was set correctly, better-sqlite3 loaded OK when tested manually with `NODE_PATH` set, but the running server process still failed — because the `.node` file had ABI 127 and system Node needed ABI 115.

**Fix:**
```bash
# 1. Rebuild for system Node v20
cd /home/opc/.9router/runtime/node_modules/better-sqlite3
bash /usr/lib/node_modules/npm/bin/node-gyp-bin/node-gyp rebuild --release --target=20.20.2 --arch=arm64 --dist-url=https://nodejs.org/dist

# 2. Symlink into app node_modules (so Next.js standalone resolves it)
ln -sf /home/opc/.9router/runtime/node_modules/better-sqlite3 /home/opc/.local/lib/node_modules/9router/app/node_modules/better-sqlite3

# 3. Restart
sudo systemctl restart 9router.service
```

**Result:** All API endpoints work — tunnel status, auth login, API keys, settings.
