---
name: reference
description: Nginx subdomain basic auth + static landing page pattern
---

# Nginx Subdomain Auth + Static Landing Page Pattern

Pattern: root domain serves a static public landing page; subdomains serve real apps but are protected with nginx basic auth so only authorized users can reach them.

## When to use

- You have one server hosting multiple services on different subdomains
- You want the root domain to be public/indexable (SEO, landing page)
- Subdomains contain admin panels, dashboards, or internal tools that should not be public
- Cloudflare is proxying all records (orange cloud)

## Architecture

```
kawaki.co.in          → static HTML landing page (public, no auth)
email.kawaki.co.in    → BillionMail admin (basic auth required)
router.kawaki.co.in   → 9router dashboard (basic auth required)
wa.kawaki.co.in       → OpenWA dashboard (basic auth required)
```

## Step 1: Create htpasswd file

```bash
# Install apache2-utils if htpasswd is missing (Oracle Linux: dnf install httpd-tools)
# Or use openssl to generate the hash:

# Create file with user 'billion' and password
openssl passwd -apr1 'YourSecurePassword' | sudo tee /etc/nginx/.htpasswd > /dev/null
# Prepend username (format: username:hash)
sudo bash -c 'sed -i "1s/^/billion:/" /etc/nginx/.htpasswd'

# Verify
cat /etc/nginx/.htpasswd
# Expected: billion:$apr1$...hash...
```

**Note:** `htpasswd` (from `httpd-tools`/`apache2-utils`) is the standard tool. On Oracle Linux 9 it may not be installed by default. Use `openssl passwd -apr1` as fallback.

## Step 2: Protect subdomains with basic auth

Each subdomain gets its own nginx server block with `auth_basic` directives:

```nginx
server {
    listen 80;
    server_name email.kawaki.co.in;

    location / {
        auth_basic "Restricted Access";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://127.0.0.1:8080;
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
```

Repeat for each subdomain (router, wa, etc.) pointing to the correct backend port.

## Step 3: Static landing page for root domain

```bash
# Create directory
sudo mkdir -p /var/www/kawaki

# Write static HTML
sudo tee /var/www/kawaki/index.html > /dev/null << 'HTML'
<!DOCTYPE html>
<html>
<head><title>Your Brand</title>...
</head>
<body>
  <h1>Brand Name</h1>
  <p>Work in progress</p>
  <a href="https://email.kawaki.co.in">Login</a>
</body>
</html>
HTML
```

## Step 4: Root domain nginx config (public, no auth)

```nginx
server {
    listen 80;
    server_name kawaki.co.in;

    root /var/www/kawaki;
    index index.html;

    # Optional: redirect specific paths
    location = /login {
        return 302 https://email.kawaki.co.in;
    }

    location / {
        try_files $uri $uri/ =404;
    }
}
```

## Step 5: SELinux — critical on Oracle Linux 9

Oracle Linux 9 has SELinux Enforcing by default. Files in `/var/www/` get `var_t` context which nginx CANNOT read → **403 Forbidden** even with correct file permissions.

```bash
# Fix SELinux context for web content
sudo semanage fcontext -a -t httpd_sys_content_t "/var/www/kawaki(/.*)?"
sudo restorecon -Rv /var/www/kawaki

# Verify
ls -laZ /var/www/kawaki/
# Should show: httpd_sys_content_t, not var_t
```

**If `semanage` is not found:**
```bash
sudo dnf install policycoreutils-python-utils -y
```

**Alternative without semanage:** copy files to nginx's default web root:
```bash
sudo cp /var/www/kawaki/index.html /usr/share/nginx/html/
sudo chown nginx:nginx /usr/share/nginx/html/index.html
```
Then point `root` in nginx config to `/usr/share/nginx/html`.

## Step 6: Test

```bash
# Public root should work without auth
curl -s -o /dev/null -w "%{http_code}" https://kawaki.co.in/
# Expected: 200

# Subdomains should require auth
curl -s -o /dev/null -w "%{http_code}" https://email.kawaki.co.in/
# Expected: 401

# With credentials should work
curl -s -o /dev/null -w "%{http_code}" -u billion:YourPassword https://email.kawaki.co.in/
# Expected: 200
```

## Common failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| 403 Forbidden on root | SELinux blocking nginx read access | `semanage fcontext` + `restorecon` OR copy to `/usr/share/nginx/html` |
| 401 on subdomain but 200 with wrong password | htpasswd file format wrong | Ensure format is `username:$apr1$hash$` not just the hash |
| nginx: [warn] conflicting server name | Two configs for same server_name | Check for duplicate `.conf` files (e.g. `openwa.conf` and `wa.kawaki.co.in.conf` both with `server_name wa.kawaki.co.in`) |
| 404 on root after config change | nginx not reloaded or wrong root path | `sudo nginx -t && sudo systemctl reload nginx`; verify `root` directive points to existing directory |

## Cloudflare-specific notes

- All subdomains should have `proxied: true` (orange cloud) in Cloudflare DNS — the auth happens at nginx level, Cloudflare just passes through
- Cloudflare SSL mode should be `flexible` if nginx only listens on port 80 (no TLS on origin) — otherwise 521 error
- The static landing page on root domain IS indexable by search engines (no `X-Robots-Tag` blocking) — add meta robots or robots.txt if you want to control indexing

## Relationship to other patterns

- This pattern works alongside `cloudflare-service-exposure` (A-record + nginx reverse proxy path)
- Does NOT require Tailscale or Cloudflare tunnels — uses standard nginx + Cloudflare proxy
- Compatible with any backend service (Docker containers, systemd services, etc.) as long as nginx can proxy to the port
