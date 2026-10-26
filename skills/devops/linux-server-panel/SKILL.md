---
name: linux-server-panel
description: Install server panels on Linux; fallback to Cockpit.
---

# linux-server-panel

## Trigger
User asks to install a web-based server management panel on a Linux server.

## Steps

### 1. Check target system
OS, arch, disk, memory, existing ports, root access:

```bash
cat /etc/os-release
uname -m
df -h /
free -h
ss -tlnp
sudo -n true && echo "root" || echo "no-root"
```

### 2. Check panel compatibility
Before installing anything, verify OS and arch are on the panel's support matrix. An unsupported install fails or produces a broken panel.

**aaPanel:**
- OS: Ubuntu, CentOS, Debian, AlmaLinux, Rocky Linux, OpenEuler
- Arch: x86_64 only — no aarch64 / ARM64
- Script: `https://www.aapanel.com/install.sh`
- **Does NOT support Oracle Linux** or ARM

See `references/aapanel-compatibility.md` for full details.

**Cockpit (fallback):**
- OS: RHEL/CentOS/Fedora, Ubuntu, Debian, and most systemd-based distros
- Arch: all (x86_64, aarch64, etc.)
- Port: 9090 HTTPS
- Install: `dnf install cockpit` (RHEL family) or `apt install cockpit` (Debian family)

### 3. Supported? Install it
Follow the panel's official install steps. Verify: list listening ports, test `curl -sk https://localhost:<port>`.

### 4. Unsupported? Pivot to Cockpit

```bash
# RHEL/CentOS/Oracle Linux family
sudo dnf install -y cockpit cockpit-storaged cockpit-files cockpit-networkmanager
sudo systemctl enable --now cockpit.socket

# Debian/Ubuntu family
sudo apt install -y cockpit cockpit-storaged cockpit-files
sudo systemctl enable --now cockpit.socket
```

Useful Cockpit plugins (RHEL family):
- `cockpit-storaged` — disks, LVM, mounts
- `cockpit-files` — web file manager
- `cockpit-networkmanager` — network config
- `cockpit-podman` — Podman containers
- `cockpit-packagekit` — software updates via GUI

### 5. Verify
```bash
ss -tlnp | grep :9090
curl -sk https://localhost:9090/issues
```

### 6. Access
- URL: `https://<server-ip>:9090`
- Login: any system user with sudo
- Self-signed cert by default — browser warning expected for internal use

## Pitfalls
- **aaPanel on Oracle Linux or ARM64**: install script detects mismatch and fails. No supported build exists — don't force it.
- **aaPanel stuck installer (Oracle Linux 9 aarch64, Sept 2026)**: the installer downloaded a 70MB Go tarball (`/tmp/go.tar.gz`) then froze at 98.8% CPU for 206+ minutes with zero progress — no `/opt/panel` or `/www` created, no network activity, no log output beyond the banner. The installer processes are root-owned and cannot be killed from a non-root user (`opc`). Result: aaPanel is not viable on this combination; use Cockpit instead. See `references/aapanel-oracle-linux-failure.md`.
- **Nginx proxy_pass without `$uri` strips nothing**: when proxying to an upstream that expects the path to be rewritten (e.g. a backend at `/` that receives requests from a subdomain), use `proxy_pass http://127.0.0.1:8080${uri};` — the `${uri}` appends the full original URI. Without it (bare `proxy_pass http://127.0.0.1:8080;`), nginx passes the URI as-is, so a request to `/billion/api/login` hits the backend as `/billion/api/login` instead of `/api/login`. This caused BillionMail's nginx config to return 404 on `/billion/api/login` because the app's actual endpoint was `/api/auth/login`. Always check whether your backend expects the path prefix to be stripped.
- **Cockpit behind Cloudflare proxy — CSP beacon conflict**: Cloudflare auto-injects `beacon.min.js` (from `static.cloudflareinsights.com`) into proxied HTML. Cockpit's own CSP is strict (`default-src 'self' http://panel.kawaki.co.in`), which blocks the beacon and any other external scripts — the browser console shows `violates the following Content Security Policy directive` and Cockpit returns `403 Forbidden` on `/cockpit/login`. Fix:
  1. Strip Cockpit's CSP in nginx: `proxy_hide_header Content-Security-Policy;` then add a permissive one with `add_header Content-Security-Policy "default-src * ..." always;`
  2. Disable Cloudflare zone features that inject/transform code: `email_obfuscation`, `server_side_exclude`, `replace_insecure_js`, `automatic_https_rewrites` → all set to `off` via Cloudflare API.
  3. Set `security_level` to `low` (or `off` if Enterprise). At `medium`, Cloudflare's WAF/transform pipeline can 403 paths like `/cockpit/login`.
  See `references/cockpit-cloudflare-csp-fix.md` for the full recipe and Cloudflare API calls.
- **Cockpit inline script CSP violations after fixing beacon**: after replacing Cockpit's CSP with a permissive one to allow Cloudflare's beacon, Cockpit's own inline `<script>` blocks in the login page HTML then violate the new CSP — browser console shows `Executing inline script violates the following Content Security Policy directive 'script-src * unsafe-inline unsafe-eval'`. **Root cause:** `'unsafe-inline'` in `script-src` only covers `on*` event handlers and `javascript:` URIs, NOT inline `<script>` blocks (CSP Level 2+). Fix: add `'unsafe-hashes'` to `script-src` and include the SHA-256 hashes from the browser console error messages (`sha256-<hash>=`). Also explicitly set `script-src-elem` to match. The session's hashes were `sha256-OD9tFkvYpAKek55XwGVEgfBO39qobmS3nWtL8CGph/0=`, `sha256-eCc+MT+H5b7jSDmxWJRH2RMW+0hyANWm1rX/wcadpEQ=`, `sha256-Pdn1P4aTogG6kHiZWabgOLf0nWLirALcvKFOv6LP8fQ=`. **Simpler alternative:** just use `script-src * 'unsafe-inline' 'unsafe-eval' 'unsafe-hashes'` without specific hashes — `'unsafe-hashes'` alone covers all inline scripts that use hashes, and combined with `'unsafe-inline'` it's permissive enough for Cockpit behind a proxy. See `references/cockpit-cloudflare-csp-fix.md` §Step 4.
- **Cockpit path routing via nginx**: Cockpit serves its SPA at `/cockpit/login`, `/cockpit/assets/*`, `/cockpit/styles/*`, etc. When proxying via nginx, the `location /` block passes the full URI to the backend, but Cockpit on port 9090 expects paths *without* a leading prefix it doesn't know about. **Correct approach:** use `location / { proxy_pass http://127.0.0.1:9090; }` (no path rewriting) — Cockpit's backend already expects `/cockpit/` prefixed paths, so pass the URI as-is. The previous recommendation to use `location /cockpit/ { proxy_pass http://127.0.0.1:9090/; }` (with trailing slash to strip prefix) is WRONG for Cockpit — it causes all asset requests (`/cockpit/static/login.js`, `/cockpit/styles/main.css`) to hit the backend without the `/cockpit/` prefix, returning 404 HTML instead of the actual JS/CSS files (browser shows `MIME type 'text/html' is not a supported stylesheet`). **Verify:** `curl -I http://127.0.0.1:9090/cockpit/static/login.js` should return `Content-Type: application/javascript`; if it returns `text/html`, the path is wrong. See `references/cockpit-nginx-exposure.md`.
- **Direct IP access to Cockpit on port 9090 times out externally**: Cockpit listens on `*:9090` but Oracle Cloud NSG/security lists or firewalld may block 9090 from the public internet. This is normal — the nginx proxy on port 80 is the public path. Don't waste time debugging 9090 direct access; verify via `curl -u user:pass http://panel.example.com/` instead.
- **Cockpit PAM authentication fails for system users on Oracle Linux 9 (SELinux)**: even with correct system user credentials, Cockpit returns 403 `Forbidden` or 401 with `pam_unix(cockpit:auth): authentication failure` in `/var/log/secure`. Root cause: `pam_sepermit.so` in `/etc/pam.d/cockpit` requires the SELinux security context of the authenticating process to match the user's expected context. Cockpit's `cockpit-tls` process runs as `cockpit_ws_t`, which doesn't match. **Fix:** comment out or remove the `pam_sepermit.so` line from `/etc/pam.d/cockpit`:
  ```bash
  sudo sed -i '/^auth.*pam_sepermit/s/^/#/' /etc/pam.d/cockpit
  ```
  Then restart cockpit: `sudo systemctl restart cockpit.socket`. After this, system users can authenticate normally. **Alternative:** use `setenforce 0` (permissive mode) temporarily — but this is a workaround, not the root fix; `pam_sepermit.so` is the actual blocker. See `references/cockpit-pam-selinux-oracle-linux.md`.
- **Cockpit nginx auth_basic + Cockpit PAM — double auth layers**: when nginx has `auth_basic` AND Cockpit has PAM auth, both layers must succeed. If nginx auth_basic has different users than Cockpit's system users, login fails at the nginx layer (401) before reaching Cockpit. **Options:** (a) use nginx auth_basic with htpasswd users that also exist as system users, or (b) remove nginx auth_basic entirely and let Cockpit handle auth via PAM (pass the `Authorization` header through: `proxy_set_header Authorization $http_authorization;`). Option (b) is simpler — one auth layer, uses real system credentials. **Verify:** direct to backend `curl -u user:pass http://127.0.0.1:9090/cockpit/login` should return 200 before adding nginx auth_basic.
- **OCI security groups block inbound ports by default**. Cockpit on 9090 isn't reachable from the public internet unless the VCN security list allows it. Use Tailscale or a VPN tunnel.
- **Port conflicts**: Cockpit defaults to 9090. If something else is on 9090, Cockpit won't start.
- **Cockpit plugins pull extra deps**: `cockpit-storaged` needs `udisks2`, `cockpit-networkmanager` needs `NetworkManager`. DNF handles this but it's worth knowing for troubleshooting.
- **Cockpit is lightweight**: system overview, terminal, logs, services, storage, network, files. NOT a full hosting panel with one-click app installs, DNS management, or database GUI. If the user needs those, they need a different tool and likely a supported OS.

## References
- `references/cockpit-nginx-exposure.md` — expose Cockpit via nginx on Oracle Linux 9: WebSocket proxy headers, openssl htpasswd fallback, basic auth, verification
- `references/aapanel-compatibility.md` — aaPanel OS/architecture compatibility and result on Oracle Linux 9.8 aarch64
- `references/aapanel-oracle-linux-failure.md` — aaPanel installer failure on Oracle Linux 9 aarch64 (stuck at 98.8% CPU for 206+ min)
- `references/cockpit-cloudflare-csp-fix.md` — Cockpit behind Cloudflare proxy: CSP beacon conflict, Cloudflare feature disabling, nginx CSP strip/replace, path routing, inline script hash fix
- `references/cockpit-pam-selinux-oracle-linux.md` — Cockpit PAM authentication failure on Oracle Linux 9: `pam_sepermit.so` blocks system user login, faillock lockout, diagnostic checklist
