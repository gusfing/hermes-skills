---
name: reference
description: BillionMail self-hosted setup on Oracle Linux 9 with nginx coexistence
---

# BillionMail on Oracle Linux 9 — Self-Hosted Setup Reference

## Prerequisites
- Docker + Docker Compose v2 plugin (`docker compose`, NOT `docker-compose`)
- git (DNS must be working for clone)
- nginx already running on port 80/443 (for other subdomains)
- Cloudflare API token with Zone:DNS:Edit scope

## Step 1: Clone
```bash
cd /opt
git clone https://github.com/aaPanel/BillionMail.git
cd BillionMail
```

## Step 2: Configure .env (avoid port conflicts)
BillionMail's default `env_init` uses HTTP_PORT=80 and HTTPS_PORT=443 — these conflict with nginx.
**Must change to non-standard ports** when nginx is already serving other subdomains.

```bash
cp env_init .env
```

Edit `.env`:
- `HTTP_PORT=8080` (was 80)
- `HTTPS_PORT=8443` (was 443)
- `BILLIONMAIL_HOSTNAME=mail.kawaki.co.in` (your sending domain)
- Keep `ADMIN_USERNAME=billion` and `ADMIN_PASSWORD=billion` (or change)
- Leave `SMTP_PORT=25` etc. as-is (internal container ports, not host-facing)

Other settings as default: `DBNAME=billionmail`, `DBUSER=billionmail`, `DBPASS=...`, `REDISPASS=...`, `TZ=Etc/UTC`, `FAIL2BAN_INIT=y`, `IPV4_NETWORK=172.66.1`

## Step 3: Create DNS record
```bash
curl -s -X POST \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -d '{"type":"A","name":"email","content":"137.23.36.156","ttl":1,"proxied":true}'
```

## Step 4: nginx reverse proxy
```bash
sudo bash -c 'cat > /etc/nginx/conf.d/email.kawaki.co.in.conf << EOF
server {
    listen 80;
    server_name email.kawaki.co.in;

    location / {
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
EOF'

sudo nginx -t && sudo nginx -s reload
```

## Step 5: Start
```bash
cd /opt/BillionMail
docker compose up -d
```

Wait for all 7 containers to be healthy:
- `billionmail-pgsql-billionmail-1` (postgres)
- `billionmail-redis-billionmail-1` (redis)
- `billionmail-rspamd-billionmail-1` (rspamd)
- `billionmail-dovecot-billionmail-1` (imap/pop)
- `billionmail-postfix-billionmail-1` (smtp)
- `billionmail-webmail-billionmail-1` (roundcube webmail)
- `billionmail-core-billionmail-1` (management UI)

Core logs show readiness: `http server started listening on [:8080]`

## Step 6: Verify
```bash
curl -sI https://email.kawaki.co.in/ | grep HTTP
# Expected: HTTP/2 200
```

## Login
- URL: `https://email.kawaki.co.in/billion` (note the `/billion` path prefix — this is the `SafePath`)
- Username: `billion`
- Password: `billion`

**Login architecture (session-based):** BillionMail uses a two-layer auth. First visit `https://email.kawaki.co.in/billion/` to get a session cookie (`billion_mail`). Then `POST /billion/api/login` returns a JWT token. API calls need BOTH the session cookie AND the JWT Bearer token. See `references/billionmail-oracle-linux-setup.md` → "Login architecture" section for full details.

## First-time admin setup (DB is empty after docker compose up -d)
BillionMail's `install.sh` seeds the admin account during interactive install, but `docker compose up -d` **does not run that initialization**. After first startup, the `account` table is empty — no admin user exists. You must create one manually.

### Create admin account (with bcrypt hash)
The `account` table stores bcrypt hashes. Inserting plaintext and expecting the service to hash it on first login does **not** work — the `Login` handler calls `bcrypt.CompareHashAndPassword` directly against whatever is in the `password` column.

**Insert with a proper bcrypt hash:**

```bash
# Generate bcrypt hash
PYTHON_HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw(b'billion', bcrypt.gensalt(rounds=10)).decode())")

sudo docker exec billionmail-pgsql-billionmail-1 psql -U billionmail -d billionmail << EOSQL
INSERT INTO account (username, password, email, status, language, last_login_time, create_time, update_time)
VALUES ('billion', '${PYTHON_HASH//\"/}', 'admin@mail.kawaki.co.in', 1, 'en', 0, EXTRACT(epoch FROM now())::int, EXTRACT(epoch FROM now())::int);
EOSQL
```

### Assign admin role
```bash
sudo docker exec billionmail-pgsql-billionmail-1 psql -U billionmail -d billionmail << EOSQL
INSERT INTO account_role (account_id, role_id)
SELECT 1, role_id FROM role WHERE role_name = 'admin';
EOSQL
```

## Login architecture (session-based, important)

BillionMail uses a **two-layer auth**: session cookie for path access + JWT token for API calls.

### Path structure
- `SafePath` in `.env` = `billion` (the URL prefix, e.g. `https://email.kawaki.co.in/billion/`)
- `WEB_BASE_PATH` must match `SafePath` exactly — the `stripWebBasePathMiddleware` strips this prefix from incoming requests before routing. If it's empty, requests to `/billion/api/*` hit BillionMail as `/billion/api/*` which doesn't match any route → 404.

### Auth flow
1. **Visit `/billion/`** → BillionMail sets a session cookie `billion_mail` and marks `safe_path_pass=true` in the session. This is REQUIRED before any API call — without it, the `HookBeforeServe` middleware blocks `/api/*` requests with "access denied" (404).
2. **POST `/billion/api/login`** with username/password → returns JWT token in `{"data":{"token":"..."}}`. The login endpoint is in the `/api` group but is whitelisted in `JWTAuthMiddleware` (no token needed to call it).
3. **API calls** → need BOTH the session cookie (`billion_mail`) AND the JWT token in `Authorization: Bearer <token>` header.

### Correct API paths (with SafePath=billion)
All API endpoints are under `/billion/api/` when accessed externally:
- Login: `POST /billion/api/login`
- List domains: `GET /billion/api/domains/list`
- Create domain: `POST /billion/api/domains/create`
- etc.

### JWT token details
The JWT secret is derived from `DBPASS` + `REDISPASS` from `.env`. Tokens are HS256 signed. Admin users get role `admin` which bypasses RBAC permission checks.

## Domain management API

### Add a domain
```bash
curl -s -X POST http://127.0.0.1:8080/billion/api/domains/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "mail.kawaki.co.in",
    "mailboxes": 50,
    "mailboxQuota": 5242880,
    "quota": 10485760,
    "rateLimit": 12,
    "catchall": "admin@kawaki.co.in"
  }'
```

Required fields: `domain`, `mailboxes`, `mailboxQuota`, `quota`, `rateLimit`. Optional: `catchall`, `hostname`, `hasbrandinfo`, `outbound_ip`.

### List domains
```bash
curl -s http://127.0.0.1:8080/billion/api/domains/list \
  -H "Authorization: Bearer $TOKEN"
```

## Outbound email / SMTP relay

**Cloudflare has NO SMTP server.** Cloudflare Email Routing is inbound-only (forwarding emails to you). There is nothing to configure in Cloudflare for BillionMail's outbound sending. The Cloudflare Email Routing API endpoint (`POST /zones/:id/email_routing`) does NOT exist — it returns 7003 "No route for that URI". Do not attempt to enable Email Routing via API.

For outbound email from BillionMail, options are:

1. **Postfix (self-hosted, already in Docker Compose)** — Postfix listens on port 25 internally. Oracle Cloud blocks outbound port 25 by default — test before assuming self-hosted sending will work (see port testing section below). If port 25 is blocked, direct sending won't work.

2. **Brevo (recommended free relay)** — 300 emails/day free, no watermark, no branding in sent emails. SMTP relay on `smtp-relay.brevo.com:587`. Sign up at brevo.com → Settings → SMTP & API → copy SMTP key. Configure in BillionMail Postfix — see `references/billionmail-oracle-linux-setup.md` → "Postfix relay configuration (Brevo example, tested)" for full working steps.

3. **Amazon SES** — $0.10 per 1000 emails. Needs production approval (sandbox mode limits to verified addresses).

4. **Other relays** — SendGrid (100/day free), Mailgun (5000/month free), SMTP2GO (1000/month free). All reachable on port 587 from Oracle.

**User preference (overridden in this session):** User originally chose "full self host no brevo" but later switched to Brevo when Oracle port 25 block was confirmed. The original "no relay" preference is documented but was overridden — treat as mutable.

### DNS records for relay-based sending (Brevo)

After adding a domain in BillionMail and configuring Brevo relay:

- **SPF** — TXT record at `mail.kawaki.co.in`: `v=spf1 include:spf.brevo.com ~all` (for Brevo relay)
- **DKIM** — TXT record at `brevo._domainkey.mail.kawaki.co.in`: Brevo provides this value after domain verification in their dashboard. Placeholder created as `placeholder - replace with Brevo DKIM value after signup` until credentials are available.
- **DMARC** — TXT record at `_dmarc.mail.kawaki.co.in`: `v=DMARC1; p=quarantine; rua=mailto:admin@kawaki.co.in`
- **PTR/rDNS** — set in Oracle Console (reverse DNS for the public IP) — improves deliverability
- **A record** — `mail.kawaki.co.in` → your server IP (for inbound/IMAP). Note: if mail.kawaki.co.in A record points to the WRONG server (e.g. a deleted VPS IP 147.93.96.248), fix it to point to the correct server IP before expecting inbound mail to work.

### DNS records for Cloudflare Email Routing inbound (optional)

Cloudflare Email Routing (free) handles inbound mail — MX records route incoming email to Cloudflare, which forwards to your configured destination. To enable:

1. Go to Cloudflare Dashboard → Email → Email Routing → Enable (CANNOT be done via API — the API endpoint doesn't exist)
2. Add destination addresses in the dashboard
3. Cloudflare auto-creates the required MX and verification TXT records

Note: Email Routing requires the domain to use Cloudflare's nameservers. It's free but the setup is dashboard-only.

## Outbound port testing on Oracle Cloud

Oracle Cloud commonly blocks outbound port 25 (SMTP direct). Test before assuming self-hosted sending will work:

```bash
# Test port 25 (SMTP direct)
curl -v --connect-timeout 5 telnet://gmail-smtp-in.l.google.com:25 2>&1 | grep -E "Connected:|timed out|Failed"

# Test port 587 (SMTP submission)
curl -v --connect-timeout 5 telnet://smtp.gmail.com:587 2>&1 | grep -E "Connected:|timed out|Failed"

# Test port 465 (SMTPS)
curl -v --connect-timeout 5 telnet://smtp.gmail.com:465 2>&1 | grep -E "Connected:|timed out|Failed"
```

**Results interpretation:**
- `Connected` → port is open, can use for SMTP relay
- `Connection timed out` → port is blocked by Oracle (or upstream firewall)

Oracle typically blocks port 25 but leaves 587/465 open. If 25 is blocked but 587/465 work, Postfix must relay through an external SMTP server (Brevo, SES, etc.) rather than sending directly.

## Postfix relay configuration (Brevo example, tested)

### Files to modify (inside Docker volume: `/opt/BillionMail/conf/postfix/conf/`)

- `main.cf` — set `relayhost = [smtp-relay.brevo.com]:587`
- `sasl_passwd` — SASL credentials: `[smtp-relay.brevo.com]:587 email:key`
- `sasl_passwd_primary` — same as above (duplicate for backup map)
- `sender_relay_maps_primary` — sender→relay mapping: `mail.kawaki.co.in [smtp-relay.brevo.com]:587`

### Steps (tested on this server)

```bash
# 1. Write config files (sudo tee or write to /tmp then sudo cp — direct write to conf/ subdir fails: permission denied)
cat > /tmp/sasl_passwd << 'EOF'
[smtp-relay.brevo.com]:587 YOUR_EMAIL:YOUR_KEY
EOF
sudo cp /tmp/sasl_passwd /opt/BillionMail/conf/postfix/conf/sasl_passwd

cat > /tmp/sender_relay_maps_primary << 'EOF'
mail.kawaki.co.in [smtp-relay.brevo.com]:587
EOF
sudo cp /tmp/sender_relay_maps_primary /opt/BillionMail/conf/postfix/conf/sender_relay_maps_primary

# 2. Rebuild hash databases inside container
sudo docker exec billionmail-postfix-billionmail-1 postmap /etc/postfix/conf/sasl_passwd
sudo docker exec billionmail-postfix-billionmail-1 postmap /etc/postfix/conf/sasl_passwd_primary
sudo docker exec billionmail-postfix-billionmail-1 postmap /etc/postfix/conf/sender_relay_maps_primary

# 3. Restart Postfix
sudo docker compose -f /opt/BillionMail/docker-compose.yml restart postfix-billionmail

# 4. Verify
sudo docker exec billionmail-postfix-billionmail-1 postconf relayhost
sudo docker exec billionmail-postfix-billionmail-1 cat /etc/postfix/conf/sasl_passwd
```

### Verifying relay works

After filling in real Brevo credentials and restarting:
```bash
# Check Postfix queue (should be empty if no stuck mail)
sudo docker exec billionmail-postfix-billionmail-1 postqueue -p

# Send a test email from BillionMail admin panel (Settings → send test email)
# or via API once domain is added
```

## Domain management in BillionMail

### Adding a domain

The domain must be added BOTH in BillionMail's database AND have DNS records configured. BillionMail's domain management API (via JWT token) is the proper way, but direct DB insert also works:

```bash
# Direct DB insert (when API is not accessible)
sudo docker exec billionmail-pgsql-billionmail-1 psql -U billionmail -d billionmail << 'SQL'
INSERT INTO domain (domain, a_record, mailboxes, mailbox_quota, quota, rate_limit, create_time, active) 
VALUES ('mail.kawaki.co.in', '137.23.36.156', 50, 5242880, 10485760, 12, EXTRACT(EPOCH FROM NOW())::integer, 1);
SQL
```

Note: The `domain_id` column doesn't exist — the primary key is `domain` (the domain name itself). Use `domain` as the column name, not `domain_id`.
### Login returns "Not Found" instead of JSON
This means the request hit nginx's default 404 page, not BillionMail. Usually caused by: (a) wrong Host header (nginx doesn't match the server_name), (b) SafePath/WEB_BASE_PATH mismatch, (c) request path not matching the configured prefix.
### Login returns "access denied" (JSON)
The request reached BillionMail but the safe_path_pass session check failed. Visit `/billion/` first to establish the session cookie, then retry the login POST with the cookie.
### WEB_BASE_PATH empty but SafePath set
The `stripWebBasePathMiddleware` checks `basePath != ""` before stripping. If `WEB_BASE_PATH` is empty in `.env`, requests with `/billion/` prefix are NOT stripped and BillionMail looks for routes at `/billion/api/*` which don't exist. Always set `WEB_BASE_PATH` to match `SafePath`.
### Admin account not created
`docker compose up -d` does NOT seed the account table. Login will fail with "access denied" regardless of `.env` ADMIN_USERNAME/PASSWORD values. Create the admin account manually with bcrypt hash.
