# Dovecot password setup for BillionMail on Oracle Linux 9

## Context
BillionMail uses Dovecot for IMAP/POP3 auth, backed by a PostgreSQL database. When creating a test mailbox manually via SQL INSERT, the password hash must match Dovecot's `default_pass_scheme` or auth fails with `passdb: user@domain auth failed`.

## Generating the hash
**Always generate the hash INSIDE the Dovecot container** — never on the host and pass it through shell. Shell escaping (bash heredocs, env vars, `docker exec bash -c`) corrupts `$` characters in bcrypt hashes (`$2a$10$...` becomes `$2a\\$10\$...`), producing an unparseable hash that Dovecot rejects.

```bash
# MD5-CRYPT (the scheme BillionMail's init.sql uses)
HASH=$(sudo docker exec billionmail-dovecot-billionmail-1 bash -c 'doveadm pw -s MD5-CRYPT -p test123 | sed "s/{MD5-CRYPT}//"')

# Or BLF-CRYPT (bcrypt)
HASH=$(sudo docker exec billionmail-dovecot-billionmail-1 bash -c 'doveadm pw -s BLF-CRYPT -p test123 | sed "s/{BLF-CRYPT}//"')
```

## Matching scheme to Dovecot config
```bash
sudo docker exec billionmail-dovecot-billionmail-1 grep default_pass_scheme /etc/dovecot/conf.d/dovecot-sql.conf.ext
```

- Config says `MD5-CRYPT` → use `doveadm pw -s MD5-CRYPT` → hash starts with `$1$`
- Config says `BCRYPT` → use `doveadm pw -s BLF-CRYPT` → hash starts with `$2y$` or `$2a$`

BillionMail's default Dovecot config uses `MD5-CRYPT`; its install.sh generates passwords via `doveadm pw -s MD5-CRYPT`.

## Inserting without shell corruption
Write SQL to a file, copy it into the DB container, execute with `psql -f`. This avoids all escaping issues:

```bash
cat > /tmp/insert_mailbox.sql << 'EOSQL'
DELETE FROM mailbox WHERE username = 'test@mail.kawaki.co.in';
DELETE FROM account WHERE username = 'test';

INSERT INTO mailbox (username, password, password_encode, full_name, is_admin, maildir, quota, local_part, domain, create_time, update_time, active, used_quota, quota_active)
VALUES ('test@mail.kawaki.co.in', '$HASH', 'md5-crypt', 'Test User', 0, 'test', 0, 'test', 'mail.kawaki.co.in', EXTRACT(EPOCH FROM now())::int, EXTRACT(EPOCH FROM now())::int, 1, 0, 1);

INSERT INTO account (username, password, email, status, language, create_time, update_time)
VALUES ('test', '$HASH', 'test@mail.kawaki.co.in', 1, 'en', EXTRACT(EPOCH FROM now())::int, EXTRACT(EPOCH FROM now())::int)
ON CONFLICT (username) DO NOTHING;

SELECT 'OK' as status, username, password_encode FROM mailbox WHERE username = 'test@mail.kawaki.co.in';
EOSQL

sudo docker cp /tmp/insert_mailbox.sql billionmail-pgsql-billionmail-1:/tmp/insert.sql
sudo docker exec billionmail-pgsql-billionmail-1 bash -c '
PGPASSWORD=NauF7ysRYyt9HTOiOn4JjIAL3QcRZnzj psql -h pgsql -U billionmail -d billionmail -f /tmp/insert.sql
'
```

## Verifying BEFORE claiming success
**Always verify auth works BEFORE telling the user the setup succeeded.** Don't claim "email sent" when the queue is empty but the relay credentials are placeholders.

```bash
# 1. Test Dovecot auth (the auth layer)
sudo docker restart billionmail-dovecot-billionmail-1
sleep 5
sudo docker exec billionmail-dovecot-billionmail-1 doveadm auth test test@mail.kawaki.co.in test123
# Must see: passdb: test@mail.kawaki.co.in auth succeeded

# 2. Test SMTP send (the delivery layer)
python3 -c "
import smtplib
from email.mime.text import MIMEText
msg = MIMEText('test')
msg['From'] = 'test@mail.kawaki.co.in'
msg['To'] = 'ks05460@gmail.com'
msg['Subject'] = 'test'
s = smtplib.SMTP('127.0.0.1', 587, timeout=15)
s.starttls()
s.login('test@mail.kawaki.co.in', 'test123')
result = s.sendmail('test@mail.kawaki.co.in', ['ks05460@gmail.com'], msg.as_string())
s.quit()
print('sendmail result:', result)
"

# 3. Check the queue AFTER sending — empty queue means delivered OR rejected/bounced
sudo docker exec billionmail-postfix-billionmail-1 postqueue -p

# 4. Check Postfix logs for actual relay activity
sudo docker logs billionmail-postfix-billionmail-1 --tail 100 | grep -iE "smtp|relay|status|deferred|bounce|brevo"

# 5. CRITICAL: verify the SASL credentials are REAL, not placeholders
sudo docker exec billionmail-postfix-billionmail-1 cat /etc/postfix/conf/sasl_passwd
# If you see YOUR_BREVO_EMAIL:YOUR_BREVO_SMTP_KEY, emails CANNOT leave the server
```

## Pitfalls
- **Placeholder SASL credentials**: BillionMail's install.sh ships with `[smtp-relay.brevo.com]:587 YOUR_BREVO_EMAIL:YOUR_BREVO_SMTP_KEY` in `/etc/postfix/conf/sasl_passwd`. Until these are replaced with real Brevo credentials, no email leaves the server — the queue looks empty because Postfix rejects at the relay stage.
- **BillionMail Dovecot SQL config missing DB password**: `/etc/dovecot/conf.d/dovecot-sql.conf.ext` must include the password in the `connect` line: `connect = host=pgsql dbname=billionmail user=billionmail password=DBPASS`. Without it, Dovecot gets `fe_sendauth: no password supplied` and can't query the mailbox table at all.
- **`INSERT ... ON CONFLICT DO NOTHING` silently skipping**: when re-inserting a mailbox that already exists with a bad hash, `ON CONFLICT DO NOTHING` does nothing — the corrupt hash persists. Always `DELETE` first.
- **Dovecot SQL connect line**: the `connect` parameter in `dovecot-sql.conf.ext` must include the DB password. The default BillionMail install may have it, but if you regenerate the config, don't forget it.
