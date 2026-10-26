---
name: postfix-smtp-relay
description: Postfix relay on secondary VPS when primary blocks port 25.
---

# Postfix SMTP Relay via Secondary VPS

## When to use
- Primary VPS (Oracle, AWS) blocks outbound port 25
- Second VPS (Hostinger, Hetzner, DO) has port 25 open
- Self-hosted relay instead of third-party service
- Primary handles Dovecot/storage/MX; relay handles outbound only

## Architecture
```
[Primary VPS] --(SMTP 587)--> [Relay VPS] --(SMTP 25)--> Gmail/recipients
  Dovecot/Storage    no auth     Postfix+DKIM     direct delivery
  MX incoming        mynetworks   signs outbound    (IP-based trust)
```

## Relay VPS setup

### Install
```bash
apt-get install -y postfix opendkim opendkim-tools
# Choose "Internet Site", mailname = mail.domain.com
```

### Postfix main.cf
```bash
myhostname = mail.domain.com
myorigin = domain.com
mynetworks = 127.0.0.0/8 [::1]/128 PRIMARY_IP/32
relayhost =
mydestination = localhost
inet_interfaces = all
smtpd_milters = local:/var/spool/postfix/private/opendkim/opendkim.sock
non_smtpd_milters = local:/var/spool/postfix/private/opendkim/opendkim.sock
milter_default_action = accept
```

### Submission port (587) — add to master.cf
```
submission inet n - y - - smtpd
  -o syslog_name=postfix/submission
  -o smtpd_tls_security_level=may
  -o smtpd_sasl_auth_enable=no
  -o milter_macro_daemon_name=ORIGINATING
```
`postfix reload` — verify: `ss -tlnp | grep :587`.

### OpenDKIM
```bash
mkdir -p /etc/opendkim/keys/domain.com
opendkim-genkey -a -b 2048 -d domain.com -s k20260923 \
  -D /etc/opendkim/keys/domain.com
chown -R opendkim:opendkim /etc/opendkim/keys/domain.com
chmod 600 /etc/opendkim/keys/domain.com/k20260923.private
```

**opendkim.conf:**
```
Socket local:/var/spool/postfix/private/opendkim/opendkim.sock
Mode sv
Domain domain.com
Selector k20260923
KeyFile /etc/opendkim/keys/domain.com/k20260923.private
```

**KeyTable:** `k20260923._domainkey.domain.com domain.com:k20260923.private`
**SigningTable:** `*@domain.com k20260923._domainkey.domain.com`
**TrustedHosts:** `127.0.0.1` + `PRIMARY_IP` + `domain.com`

Socket dir: `mkdir -p /var/spool/postfix/private/opendkim && chown opendkim:opendkim /var/spool/postfix/private/opendkim`

```bash
systemctl enable --now opendkim
systemctl restart postfix
ls -la /var/spool/postfix/private/opendkim/opendkim.sock
```

### DNS records
| Type | Name | Value |
|------|------|-------|
| A | mail.domain.com | RELAY_IP (unproxied) |
| TXT | domain.com | v=spf1 ip4:PRIMARY_IP ip4:RELAY_IP ~all |
| TXT | k20260923._domainkey.domain.com | v=DKIM1; h=sha256; k=rsa; p=<pubkey> |

Pubkey from `cat /etc/opendkim/keys/domain.com/k20260923.txt`.

### Cloudflare API notes
- Token needs Zone:DNS:Edit scope
- Test first: `curl -s -H "Authorization: Bearer $TOKEN" "https://api.cloudflare.com/client/v4/zones?name=domain.com"`
- SPF must include BOTH IPs

### Primary VPS config
```bash
postconf -e "relayhost = [RELAY_IP]:587"
postconf -e "smtp_tls_security_level = may"
postconf -e "smtp_tls_CAfile = /etc/ssl/certs/ca-certificates.crt"
postfix reload
```

## Pitfalls

**DKIM socket missing:** Check `systemctl status opendkim`, `journalctl -u opendkim | grep socket`. Fix: `mkdir -p /var/spool/postfix/private/opendkim && chown opendkim:opendkim /var/spool/postfix/private/opendkim`.

**Milter connection refused:** Socket path mismatch between opendkim.conf and main.cf. Fix perms: `chmod 777 /var/spool/postfix/private/opendkim/`.

**DKIM key corrupt:** Regenerate: `rm -rf /etc/opendkim/keys/domain.com && opendkim-genkey ...`.

**Gmail 550 5.7.26:** DKIM/SPF not passing. Check DNS propagation (`dig TXT k20260923._domainkey.domain.com`), verify SPF includes relay IP.

**Postfix bounces (No MX host):** `mail.domain.com` A record missing. Postfix does MX lookup for local delivery.

**Oracle outbound blocked:** Verify: `timeout 5 bash -c 'echo > /dev/tcp/RELAY_IP/587'`. If closed, use port 465 or third-party relay.

**Cloudflare API 9106 auth error:** Placeholder/revoked token. Test with zone lookup first.

**Local mail loop:** Don't test with local addresses — Postfix appends domain → loop. Test with external Gmail.
