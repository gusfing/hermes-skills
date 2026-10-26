---
name: email-from-cloud
description: Send email from cloud servers where port 25 is blocked.
tags:
  - email
  - smtp
  - oraclecloud
  - port25
---

# Email from Cloud Servers

Send email from a cloud VPS or container where outbound port 25 is blocked.
Use external SMTP relays on port 587/465 directly from scripts. Never install
a local MTA for notification-style email.

## Trigger conditions

Use when:
- User asks to send email from a cloud server or script
- "send me emails" from automation/messaging bridge
- Setting up alert/notification emails from a VPS
- Diagnosing why SMTP fails from cloud host

Skip when:
- Full mail server needed (Postfix+Dovecot+MX) — different task
- Reading email via CLI (use `himalaya`, `agentmail`)

## Port 25 is blocked — use external relay

Cloud providers block outbound port 25 by default. Installing Postfix locally
does not fix this — the outbound connection to remote MX on port 25 is blocked
at the network level. The fix is an external SMTP relay on 587/465.

## Verified open relays (Oracle Linux 9 aarch64)

TCP-probed and confirmed open:

| Host | 587 | 465 |
|---|---|---|
| smtp.sendgrid.net | yes | yes |
| smtp.mailgun.org | yes | yes |
| smtp.resend.com | yes | yes |
| smtp.postmarkapp.com | yes | — |

Gmail (`smtp.gmail.com:587`) requires OAuth2 or App Password — avoid, use a
relay instead.

## smtplib pattern

```python
import os, smtplib
from email.message import EmailMessage

msg = EmailMessage()
msg['Subject'] = subject
msg['From'] = os.environ['EMAIL_FROM']
msg['To'] = recipient
msg.set_content(body)

with smtplib.SMTP(os.environ['SMTP_HOST'], 587) as s:
    s.starttls()
    s.login(os.environ['SMTP_USER'], os.environ['SMTP_PASS'])
    s.send_message(msg)
```

Credentials from env — never hardcoded. Username/password is for the relay
service, not a personal email account.

## CLI tools for Outlook/M365

When user wants Outlook CLI (not just SMTP email), these exist. **`outlook-commander` does not exist on npm — 404, do not retry.**

| Tool | Install | Notes |
|---|---|---|
| `@pnp/cli-microsoft365` | `npm i -g @pnp/cli-microsoft365` | Full M365 CLI, needs Azure AD OAuth |
| `msgcli` | `npm i -g msgcli` | Agent-first Outlook CLI |
| `nylas` CLI | macOS/brew only | `nylas auth login --provider microsoft` |

For Linux SMTP email, `smtplib` is simpler than any CLI tool.

## User preference

"Send me emails dumb" = plain, short, factual body. No AI summary, no HTML
fluff, no tracking pixels, no preamble. Just what happened.

## Anti-patterns

- Installing Postfix for notifications — queues but can't deliver (port 25 blocked)
- Retrying `npm install outlook-commander` — package doesn't exist (404)
- Gmail username/password directly on 587 — needs OAuth2/App Password
- Hardcoding SMTP credentials
- AI summaries in notification emails (unless user asks)

## Verification

After sending:
1. `smtplib.send_message()` raises on failure — catch and report
2. Check recipient inbox (and spam folder)
3. For automation-triggered emails, verify the trigger fired (queue file,
   webhook log, bridge stdout)

## References

- `references/verified-smtp-relays.md` — table of probed hosts, smtplib boilerplate
