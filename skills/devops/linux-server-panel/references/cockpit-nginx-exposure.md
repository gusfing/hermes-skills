# Cockpit Exposure via nginx on Oracle Linux 9

## When to use
User wants Cockpit (the system panel already installed on the server) exposed publicly via a subdomain with basic auth, instead of using a different panel installer.

## Prerequisites
- Cockpit already installed (`cockpit` package, not necessarily running)
- Root/sudo access on the VPS
- Nginx already installed and running
- A subdomain DNS record pointing to the VPS IP (Cloudflare or direct)

## Step 1: Enable Cockpit

```bash
# Start and enable the socket (handles TLS termination internally)
sudo systemctl enable --now cockpit.socket

# Verify it's listening
ss -tlnp | grep 9090
```

## Step 2: Configure nginx reverse proxy

Cockpit uses WebSockets for its terminal and real-time features. The proxy must handle the Upgrade header or the UI will be broken (login page loads but terminal/shell won't connect).

```bash
sudo tee /etc/nginx/conf.d/cockpit.conf > /dev/null << 'EOF'
server {
    listen 80;
    server_name panel.example.com;

    location / {
        proxy_pass http://127.0.0.1:9090;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
}
EOF
```

Key things:
- `proxy_set_header Upgrade` and `Connection "upgrade"` are **mandatory** for Cockpit's WebSocket features
- `proxy_read_timeout 86400` prevents WebSocket connections from timing out during idle terminal sessions
- The `auth_basic` lines add HTTP basic auth in front of Cockpit (defense in depth — Cockpit already has its own auth)

## Step 3: Create htpasswd when `htpasswd` binary is not available

On minimal Oracle Linux installs, `httpd-tools` (which provides `htpasswd`) is often not installed. Do NOT install it just for this — use openssl instead:

```bash
# Generate Apache MD5 hash for the password
HASH=$(openssl passwd -apr1 'your-password-here')

# Write htpasswd file
echo "username:$HASH" | sudo tee /etc/nginx/.htpasswd > /dev/null
sudo chmod 644 /etc/nginx/.htpasswd
```

Format: `username:$apr1$...` (one line per user). Multiple users: append more `user:hash` lines.

## Step 4: Test and reload nginx

```bash
sudo nginx -t          # syntax check — must pass before reload
sudo systemctl reload nginx
```

## Step 5: Verify externally

```bash
# Without auth — should get 401
curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 http://panel.example.com/

# With auth — should get 200 (Cockpit login page HTML)
curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 -u user:password http://panel.example.com/
```

Expected: 401 without credentials, 200 with credentials (Cockpit login page).

**Note:** Direct access to port 9090 from outside may time out even when nginx proxy works — this is normal if the VPS firewall blocks 9090 but allows 80. The nginx proxy on port 80 is the public path; direct 9090 access is not required.

## What Cockpit gives you
- System overview (CPU, memory, disk, network)
- Terminal (web-based shell)
- Logs (journald viewer)
- Services (systemd service management)
- Storage (disks, mounts, LVM)
- Network (interfaces, firewalld)
- Podman containers (if `cockpit-podman` installed)
- Software updates (if `cockpit-packagekit` installed)

It is NOT a full hosting panel (no one-click app installs, no DNS management, no database GUI). If you need those, Cockpit won't provide them.

## Installed plugins (Oracle Linux / RHEL family)

```bash
sudo dnf install -y cockpit-storaged cockpit-files cockpit-networkmanager cockpit-podman cockpit-packagekit
sudo systemctl restart cockpit.socket
```

- `cockpit-storaged` — disks, LVM, mounts (needs `udisks2`)
- `cockpit-files` — web file manager
- `cockpit-networkmanager` — network config (needs `NetworkManager`)
- `cockpit-podman` — Podman containers
- `cockpit-packagekit` — software updates GUI

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `curl` to panel subdomain times out (000) | VPS firewall/NSG blocks port 80 | Open port 80 in firewalld + cloud security list |
| 502 from nginx | Cockpit not running | `sudo systemctl start cockpit.socket` |
| Login page loads but terminal doesn't connect | Missing WebSocket proxy headers | Add `Upgrade`/`Connection` headers to nginx config |
| 401 even with correct credentials | htpasswd file wrong format or nginx can't read it | Check file exists, is readable, format is `user:hash` |
| `htpasswd: command not found` | `httpd-tools` not installed | Use `openssl passwd -apr1` instead (see Step 3) |
| Backend returns 404 on proxied paths (e.g. `/panel/api/login` → 404 but `/api/login` → 200) | nginx `proxy_pass` without `${uri}` — path not rewritten. Bare `proxy_pass http://127.0.0.1:8080;` passes the URI as-is. If the backend expects paths without the subdomain prefix, use `proxy_pass http://127.0.0.1:8080${uri};` so nginx appends the original URI to the upstream. Always verify what path the backend expects. |
| **Browser console: CSP violation for `beacon.min.js`** | Cockpit's own CSP blocks Cloudflare's auto-injected beacon script. Cloudflare injects `static.cloudflareinsights.com/beacon.min.js` into proxied HTML by default. | See `references/cockpit-cloudflare-csp-fix.md` for the full fix: strip CSP in nginx + disable Cloudflare transformation features |
| **`/cockpit/login` returns 403 via Cloudflare proxy** | Cloudflare zone features (`email_obfuscation`, `server_side_exclude`, `replace_insecure_js`, `security_level: medium`) block or transform the response. | Disable those features via Cloudflare API; set security_level to `low`; see `references/cockpit-cloudflare-csp-fix.md` |
| **`/cockpit/login` returns 404 via nginx** | nginx `location /` passes `/cockpit/login` as-is to backend, but Cockpit expects paths without the `/cockpit/` prefix. | Use `location /cockpit/ { proxy_pass http://127.0.0.1:9090/; }` — the trailing slash on `proxy_pass` strips the prefix. See `references/cockpit-cloudflare-csp-fix.md` |
| Direct IP:9090 times out from outside | Port 9090 blocked at firewall/NSG (normal — nginx on port 80 is the public path) | Don't debug 9090 direct access; verify via `curl -u user:pass http://panel.example.com/` |

## Oracle Linux / firewalld notes

On Oracle Linux 9, firewalld is typically running. Cockpit's port 9090 may already be open (check `firewall-cmd --list-all`). If not:

```bash
sudo firewall-cmd --add-port=9090/tcp --permanent
sudo firewall-cmd --reload
```

But if nginx is proxying on port 80, only port 80 needs to be open externally — Cockpit's 9090 only needs to be reachable from localhost.
