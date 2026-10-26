# SELinux blocks Cockpit authentication on Oracle Linux

**Problem:** Cockpit login returns `403 Forbidden` or `401 Unauthorized` with no clear reason, even though the user exists and the password is correct. Works via SSH but not via Cockpit web interface.

**Root cause:** SELinux (enforcing mode) + `pam_sepermit.so` in `/etc/pam.d/cockpit`.

## Diagnosis

Check these in order:

```bash
# 1. Is SELinux enforcing?
sestatus | grep "Current mode"

# 2. Check /var/log/secure for PAM failures
sudo tail -20 /var/log/secure | grep -iE "cockpit|opc|pam|auth|sepermit"

# 3. Check cockpit-tls process SELinux context
ps -eZ | grep cockpit

# Expected: system_u:system_r:cockpit_ws_t:s0
# This context cannot read /etc/shadow for password verification
# when pam_sepermit.so is active.
```

Look for these log entries in `/var/log/secure`:
```
unix_chkpwd[...]: password check failed for user (opc)
cockpit-session[...]: pam_unix(cockpit:auth): authentication failure
```

## Fix

### Option A — Disable pam_sepermit (quick, no reboot)

```bash
# Backup first
sudo cp /etc/pam.d/cockpit /etc/pam.d/cockpit.bak

# Comment out pam_sepermit.so
sudo sed -i 's/^auth.*pam_sepermit/#auth       required     pam_sepermit.so/' /etc/pam.d/cockpit

# Verify
head -5 /etc/pam.d/cockpit
# Should show: #auth       required     pam_sepermit.so
```

Then restart Cockpit (or it picks up the change automatically):
```bash
sudo systemctl restart cockpit
```

**Test:** `curl -s -o /dev/null -w '%{http_code}' -u opc:PASSWORD http://localhost:9090/cockpit/login`

Expected: `200` (or `401` if wrong password, NOT `403`).

### Option B — Set SELinux to permissive (temporary, for testing)

```bash
sudo setenforce 0
```

Test Cockpit login. If it works, SELinux was the blocker. Revert with `sudo setenforce 1` and use Option A for a permanent fix, or create proper SELinux policy.

### Option C — Create a dedicated Cockpit user (if you don't want to use opc)

```bash
# Create a system user for Cockpit access
sudo useradd -m -s /bin/bash cockpitadmin
echo "cockpitadmin:YourPassword123" | sudo chpasswd

# Test
curl -s -o /dev/null -w '%{http_code}' -u cockpitadmin:YourPassword123 http://localhost:9090/cockpit/login
```

## nginx integration

When Cockpit is behind nginx (common on Oracle Linux), the 403 can also come from nginx's `auth_basic` if the htpasswd user doesn't exist as a Linux system user. Cockpit authenticates via PAM against real system accounts.

**Correct setup:**
- Let nginx pass through all auth to Cockpit (no `auth_basic` in nginx)
- Cockpit handles auth via PAM against system users (`opc`, `cockpitadmin`, etc.)
- nginx only proxies: `proxy_pass http://127.0.0.1:9090`

**Broken setup:**
- nginx has `auth_basic "Restricted"` with an htpasswd user like `paneladmin`
- nginx validates the user, then forwards Basic auth headers to Cockpit
- Cockpit sees `paneladmin` but has no such Linux user → 403

## CSP when Cockpit is behind nginx + Cloudflare

If Cockpit is proxied through nginx and Cloudflare (proxied DNS), you may get CSP errors in the browser:

1. **Cloudflare injects scripts** — `email_obfuscation`, `server_side_exclude`, `replace_insecure_js` all add inline scripts
2. **Cockpit sends restrictive CSP** — blocks Cloudflare's injected scripts
3. **Browser blocks** — "Refused to execute script... violates CSP"

**Fix (at nginx layer):**
```nginx
location / {
    proxy_pass http://127.0.0.1:9090;
    proxy_hide_header Content-Security-Policy;
    add_header Content-Security-Policy "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; script-src * 'unsafe-inline' 'unsafe-eval'; connect-src * ws: wss:; img-src * data:; style-src * 'unsafe-inline'; font-src *; object-src *; frame-src *;" always;
    # ... other proxy headers
}
```

Also disable the offending Cloudflare features via API (see `cloudflare-dns-api` skill, "Zone Settings" section).

## Related

- `cloudflare-dns-api` skill — Zone Settings section for toggling Cloudflare features
- `/etc/pam.d/cockpit` — PAM config for Cockpit auth
- `/etc/cockpit/disallowed-users` — users blocked from Cockpit (default: root)
