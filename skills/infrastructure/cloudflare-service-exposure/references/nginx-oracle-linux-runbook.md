# nginx reverse proxy on Oracle Linux 9 — runbook

Proxy port 80/443 to a local app (e.g. OpenWA on 2785) so a Cloudflare proxied (`proxied: true`) A record can reach it over standard ports.

## Install

```bash
sudo dnf install -y nginx
```

## Config

```bash
sudo tee /etc/nginx/conf.d/openwa.conf > /dev/null <<'EOF'
server {
    listen 80;
    server_name wa.kawaki.co.in;   # <-- your proxied subdomain

    location / {
        proxy_pass http://127.0.0.1:2785;   # <-- your app port
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_buffering off;
        proxy_read_timeout 86400s;
    }
}
EOF
```

For persistent WebSocket connections (whatsapp-web.js, live dashboards), the `Upgrade`/`Connection` headers and `proxy_read_timeout` are what keep the connection from being cut by nginx.

## Firewall (if firewalld is the active firewall)

```bash
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=2785/tcp   # if app is reached directly too
sudo firewall-cmd --reload
```

## SELinux (Oracle Linux 9 — mandatory, not optional)

Oracle Linux 9 ships with SELinux in enforcing mode. When nginx tries to connect to a non-standard port (anything other than the well-known HTTP/HTTPS ports), the connection is denied at the SELinux layer and nginx logs:

```
connect() to 127.0.0.1:2785 failed (13: Permission denied) while connecting to upstream
```

This returns **502** from nginx even though the backend is healthy and reachable via `curl` directly. It is a policy denial, not a network or config error.

**Fix — allow nginx outbound network connections:**

```bash
sudo setsebool -P httpd_can_network_connect 1
```

`-P` makes it persistent across reboots. Verify:

```bash
getsebool httpd_can_network_connect
# should print: httpd_can_network_connect --> on
```

If `setsebool` is not found, install the SELinux userspace tools first:

```bash
sudo dnf install -y policycoreutils-python-utils
```

**Diagnostic checklist when nginx returns 502 to a healthy backend:**

1. Confirm the backend is reachable directly: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:<APP_PORT>/health` → expect 200.
2. Check nginx error log: `sudo tail -5 /var/log/nginx/error.log` — if it says `Permission denied` on the connect(), it is SELinux.
3. Apply `setsebool -P httpd_can_network_connect 1` and retest.

Do NOT disable SELinux outright (`setenforce 0`) as a fix — that disables the whole security policy on the box. Use the boolean.

## Start

```bash
sudo systemctl enable --now nginx
```

## Verify

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:2785/api/health/ready
# expect 200
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80/
# expect 200 (nginx → app)
```

## HTTPS options

- **Cloudflare Flexible SSL** (orange cloud): CF terminates HTTPS at the edge, forwards HTTP to your nginx on port 80. No cert needed on the VPS. Downside: traffic between CF edge and VPS is plaintext (fine on a private VCN; not fine over a public untrusted path).
- **Full (strict) SSL**: install a real cert on nginx (Let's Encrypt via `certbot` or an origin CA cert from Cloudflare). CF terminates HTTPS, validates your origin cert, forwards HTTPS to the VPS on port 443. Requires port 443 open and a cert on the VPS.
- **Tunnel**: no nginx, no cert, no open port. See the skill body.
