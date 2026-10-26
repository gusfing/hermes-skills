# Cockpit PAM + SELinux Authentication on Oracle Linux 9

## Problem

Cockpit returns 403 Forbidden or 401 when system users try to log in, even with correct credentials. `/var/log/secure` shows:
```
pam_unix(cockpit:auth): authentication failure; ... user=opc
unix_chkpwd[...]: password check failed for user (opc)
```

Root cause: `pam_sepermit.so` in `/etc/pam.d/cockpit` requires the SELinux security context of the authenticating process to match the user's expected context. Cockpit's `cockpit-tls` process runs as `cockpit_ws_t`, which doesn't satisfy `pam_sepermit`.

## Fix

Comment out `pam_sepermit.so` in the PAM config:

```bash
sudo sed -i '/^auth.*pam_sepermit/s/^/#/' /etc/pam.d/cockpit
```

Then restart Cockpit:

```bash
sudo systemctl restart cockpit.socket
```

## Verification

```bash
# Direct to backend — should return 200 with correct system credentials
curl -s -o /dev/null -w '%{http_code}' \
  -u opc:password \
  http://127.0.0.1:9090/cockpit/login

# Expected: 200
```

## Why not setenforce 0?

`setenforce 0` (permissive mode) is a workaround — it disables SELinux enforcement entirely, which is overkill. The actual blocker is `pam_sepermit.so` specifically requiring context matching. Removing/commenting that one PAM line is the targeted fix.

If SELinux is already in permissive mode and login still fails, the issue is something else (wrong password, account locked by `pam_faillock`, user in `/etc/cockpit/disallowed-users`).

## Alternative approaches

1. **Create a dedicated Cockpit user** instead of using an existing system user — avoids SELinux context issues entirely but adds a user to manage.

2. **Use nginx auth_basic without Cockpit PAM** — let nginx handle auth via htpasswd, pass the Authorization header through to Cockpit: `proxy_set_header Authorization $http_authorization;`. Simpler but means two separate credential sets to manage.

3. **Disable pam_sepermit globally** (not recommended) — affects all services using it.

## pam_faillock account lockout

Oracle Linux 9's `pam_faillock` locks an account for 1800 seconds (30 min) after 5 failed auth attempts. If a user can't log in even after fixing the PAM config, check:

```bash
sudo faillock --user <username>
```

Clear the lock:

```bash
sudo rm -f /var/run/faillock/<username>
```

## Diagnostic checklist

| Symptom | Cause | Check |
|---------|-------|-------|
| 403 Forbidden with correct system credentials | `pam_sepermit.so` blocking SELinux context mismatch | `grep pam_sepermit /etc/pam.d/cockpit` |
| 401 with correct credentials | Wrong password, account locked, or user disallowed | `/var/log/secure` for `authentication failure`; `faillock --user <user>`; check `/etc/cockpit/disallowed-users` |
| 401 with correct credentials (SELinux permissive) | `pam_faillock` locked after 5 failed attempts | `sudo faillock --user <user>`; clear with `sudo rm -f /var/run/faillock/<user>` |
| User not in `/etc/shadow` | User doesn't exist or has no password set | `id <user>`; `sudo grep ^<user>: /etc/shadow` |
| 403 even after removing pam_sepermit | User is `root` (blocked by default) or in disallowed-users | Check `/etc/cockpit/disallowed-users` |
| Password works via `su` but not Cockpit | `pam_sepermit.so` or `pam_faillock` | Check PAM config and faillock status |

## See also

- `references/cockpit-cloudflare-csp-fix.md` — Cockpit behind Cloudflare proxy: CSP, path routing, Cloudflare feature disabling
- `references/cockpit-nginx-exposure.md` — general Cockpit nginx exposure (WebSocket headers, htpasswd via openssl, basic auth)
