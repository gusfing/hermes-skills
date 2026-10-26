# Full Install Migration — x86_64 container → Oracle ARM64

## Why full clone fails across architectures
- **Cannot copy:** `node_modules`, browser binaries, uv caches, Python venv.
- **Root cause:** this container is `x86_64`, Oracle Free Tier is `aarch64`/ARM64. Binaries, npm native modules, and pip wheels are architecture-specific.
- **Recreate on Oracle:** run `npm install`, `npx playwright install chromium`, `uv venv .venv && uv pip install -e '.[all]'`.

## Portable data/config layers

```bash
# On source machine
mkdir -p /tmp/hermes-clone
tar czf /tmp/hermes-clone/data.tar.gz \
  -C /opt/data \
    skills plugins chrome-profiles .camofox outreach state spawn-trees \
  --exclude='node_modules' \
  --exclude='.cache/mesa_shader_cache_db'
```

| Source path | What it contains |
|---|---|
| `/opt/data/skills/` | All installed skills (48 MB) |
| `/opt/data/plugins/` | Custom plugins |
| `/opt/data/chrome-profiles/` | Chrome user data dirs, includes `wa_account_a` WhatsApp session |
| `/opt/data/.camofox/` | Camofox cookies + profile IDs |
| `/opt/data/outreach/` | Outreach dashboard, sequences, campaigns, OpenWA/WASender refs |
| `/opt/data/state/` | Agent runtime state |
| `/opt/data/spawn-trees/` | Delegation spawn trees |

## Non-portable layers (rebuild on Oracle)

| Path | Why | Rebuild command |
|---|---|---|
| `/opt/hermes/node_modules/` | x86 native modules | `npm install` in `/opt/hermes` |
| `/opt/data/.agent-browser/` | Chrome binaries | auto-downloaded by agent |
| `/opt/data/.cache/puppeteer/` | Chromium binaries | `npx playwright install chromium` |
| `/opt/data/.cache/camoufox/` | Camoffox browser binary | auto-downloaded on first use |
| `/opt/data/.cache/uv/` | uv interpreter/wheel caches | fresh uv fetch on Oracle |
| `/opt/hermes/.venv/` | Python venv + x86 wheels | `uv venv .venv && uv pip install -e '.[all]'` |
| `/opt/data/.cache/mesa_shader_cache_db/` | GPU shader cache | skip; regenerates |

## Migration recipe

1. **Backup portable data on source:**
   ```bash
   mkdir -p /tmp/hermes-clone
   tar czf /tmp/hermes-clone/data.tar.gz \
     -C /opt/data \
       skills plugins chrome-profiles .camofox outreach state spawn-trees \
     --exclude='node_modules' \
     --exclude='.cache/mesa_shader_cache_db'
   ```

2. **Transfer to Oracle:** `scp`/`sftp` `/tmp/hermes-clone/data.tar.gz` to `opc@<oracle-ip>:/tmp/`.

3. **Fresh Hermes install on Oracle:**
   ```bash
   # After disk expand and home wipe
   GIT_TERMINAL_PROMPT=0 git clone --depth 1 https://github.com/nousresearch/hermes-agent.git ~/.hermes/hermes-agent
   cd ~/.hermes/hermes-agent
   ~/.hermes/bin/uv venv .venv
   ~/.hermes/bin/uv pip install -e '.[all]' --python .venv/bin/python
   # Patch launchers, set PATH in .bashrc + .bash_profile
   ```

4. **Restore data on Oracle:**
   ```bash
   sudo mkdir -p /opt/data
   sudo chown opc:opc /opt/data
   tar xzf /tmp/hermes-clone.tar.gz -C /opt/data
   cd /opt/data/outreach && npm install
   ```

5. **Rebuild browser binaries:**
   ```bash
   npx playwright install chromium
   ```

6. **Verify:**
   ```bash
   hermes --version
   hermes doctor
   ls /opt/data/skills/social-media/whatsapp-web-outreach/SKILL.md
   ls /opt/data/chrome-profiles/wa_account_a/
   ls /opt/data/outreach/dashboard/
   ```

## Session-specific notes

- Chrome profile `/opt/data/chrome-profiles/wa_account_a` is reused verbatim on Oracle; WhatsApp login state survives migration.
- Outreach dashboard runs locally at `http://127.0.0.1:3001`; QR is at `/opt/data/outreach/dashboard/public/qr.png`.
- Dashboard must be accessed via SSH port-forward from Windows; Tailscale host-header check blocks direct access.
- Oracle login shells need PATH export in both `.bashrc` and `.bash_profile`.
