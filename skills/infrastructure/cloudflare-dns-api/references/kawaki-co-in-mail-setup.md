# kawaki.co.in Mail DNS Setup (Hostinger Relay)

## Architecture
- **Oracle VPS (137.23.36.156):** Dovecot IMAP/POP3, BillionMail storage, Postfix on port 587/465 (submission)
- **Hostinger VPS (147.93.96.248):** Postfix SMTP relay on port 25 + 587, OpenDKIM signing
- **Incoming mail:** MX → mail.kawaki.co.in → Oracle (Dovecot)
- **Outgoing mail:** Oracle Postfix `relayhost = [147.93.96.248]:587` → Hostinger → direct to Gmail/recipients

## DNS Records (Cloudflare zone: 29b3e217548ac234542d3ee0f1b27ae8)

### Required records

| Type | Name | Content | Proxied | Purpose |
|------|------|---------|---------|----------|
| A | mail.kawaki.co.in | 147.93.96.248 | false | Incoming MX target + outgoing HELO |
| TXT | mail.kawaki.co.in | v=spf1 ip4:137.23.36.156 ip4:147.93.96.248 ~all | false | SPF — both Oracle + Hostinger IPs |
| TXT | k20260923._domainkey.kawaki.co.in | v=DKIM1; h=sha256; k=rsa; p=<public_key> | false | DKIM signing key |

### DKIM TXT record format
Multi-string TXT records in Cloudflare API:

```bash
curl -s -X POST \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -d '{"type":"TXT","name":"k20260923._domainkey.kawaki.co.in",
       "content":"v=DKIM1; h=sha256; k=rsa; "
                "p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...",
       "ttl":120,"proxied":false}'
```

The `p=` value is the public key from `/etc/opendkim/keys/kawaki.co.in/k20260923.txt` (the `.txt` file, NOT the `.private` file).

### SPF record
The SPF must include BOTH the Oracle IP (for incoming/ outbound from Oracle) AND the Hostinger IP (for relayed outbound):

```
v=spf1 ip4:137.23.36.156 ip4:147.93.96.248 ~all
```

Do NOT include `include:spf.brevo.com` — that was the old placeholder.

## Pitfalls observed

### Cloudflare API auth failures
- **Symptom:** `{"success":false,"errors":[{"code":9106,"message":"Authentication failed (status: 400)"}]}`
- **Cause:** Using a placeholder token like `YOUR_C...OKEN` or an expired/revoked token
- **Fix:** Verify the token works with a simple query first: `curl -s -H "Authorization: Bearer $TOKEN" "https://api.cloudflare.com/client/v4/zones/$ZONE_ID"` — must return `{"success":true}`
- **Note:** The token used in this session was `REDACTED_CLOUDFLARE_TOKEN` — rotate after use

### DNS propagation delay
After updating `mail.kawaki.co.in` A record, Hostinger Postfix bounces mail with:
```
Host or domain name not found. Name service error for name=mail.kawaki.co.in type=AAAA
```
This happens because Postfix does MX lookups and the AAAA record doesn't exist. Fix: ensure the A record is set, and optionally add an AAAA record or disable IPv6 in Postfix (`inet_protocols = ipv4`).

### Mail loop when testing locally
Sending `mail -s test sysadmin@favouritecampus` on Hostinger causes Postfix to append the domain (`kawaki.co.in`) making `sysadmin@favouritecampus.kawaki.co.in` which resolves to the same server → loop. Test with external addresses (Gmail) instead.

### DKIM key corrupt
**Symptom:** `opendkim: KeyTable entry for 'k20260923._domainkey.kawaki.co.in' corrupt`
**Fix:** Regenerate keys:
```bash
sudo rm -rf /etc/opendkim/keys/kawaki.co.in
sudo mkdir -p /etc/opendkim/keys/kawaki.co.in
sudo opendkim-genkey -a -b 2048 -d kawaki.co.in -s k20260923 -D /etc/opendkim/keys/kawaki.co.in
sudo chown -R opendkim:opendkim /etc/opendkim/keys/kawaki.co.in
sudo chmod 600 /etc/opendkim/keys/kawaki.co.in/k20260923.private
```
Then update KeyTable and SigningTable, restart OpenDKIM.

### OpenDKIM socket not created
**Symptom:** `postfix/cleanup: warning: connect to Milter service local:.../opendkim.sock: No such file or directory`
**Cause:** OpenDKIM service running but socket directory doesn't exist or wrong permissions
**Fix:** Ensure the socket directory exists with correct ownership:
```bash
sudo mkdir -p /var/spool/postfix/private/opendkim
sudo chown opendkim:opendkim /var/spool/postfix/private/opendkim
sudo chmod 755 /var/spool/postfix/private/opendkim
sudo systemctl restart opendkim
```
Verify socket appears: `ls -la /var/spool/postfix/private/opendkim/opendkim.sock`

### Postfix not listening on port 587
**Symptom:** Oracle cannot connect to Hostinger on port 587; `ss -tlnp | grep :587` shows nothing
**Cause:** Postfix default only listens on port 25; submission service not configured
**Fix:** Add submission to `/etc/postfix/master.cf`:
```
submission inet n       -       y       -       -       smtpd
  -o syslog_name=postfix/submission
  -o smtpd_tls_security_level=may
  -o smtpd_sasl_auth_enable=no
  -o milter_macro_daemon_name=ORIGINATING
```
Then `postfix reload` and verify with `ss -tlnp | grep :587`.

### Oracle Postfix TLS error (454)
**Symptom:** `smtplib.SMTPResponseException: (454, b'4.7.0 TLS not available due to local problem')`
**Cause:** Oracle Postfix container missing CA certificates or TLS misconfigured
**Fix:** Ensure CA certs in container, configure `smtp_tls_CAfile = /etc/ssl/certs/ca-certificates.crt`, set `smtp_tls_security_level = may`.

### Oracle→Hostinger network blocking
**Symptom:** `telnet 147.93.96.248 587` times out from Oracle VPS; SSH port 2222 also times out
**Cause:** Oracle Cloud firewall/security lists block outbound ports 25, 587, 2222 from the instance
**Workaround:** Ports 80/443 are open from Oracle — use HTTPS-based relay or a relay service that accepts on 443. Self-hosted relay on Hostinger port 587 does NOT work from Oracle.
**Alternative:** Use a relay service (SendGrid, SMTP2GO, Amazon SES) that accepts connections from Oracle on port 587.
