# Verified SMTP Relay Hosts

TCP-probed from Oracle Linux 9 aarch64.

| Host | 587 | 465 |
|---|---|---|
| smtp.sendgrid.net | yes | yes |
| smtp.mailgun.org | yes | yes |
| smtp.resend.com | yes | yes |
| smtp.postmarkapp.com | yes | — |

smtp.gmail.com:587 needs OAuth2/App Password — use a relay instead.

## smtplib boilerplate

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

## Outlook CLI

`outlook-commander` does not exist on npm — 404. Use `@pnp/cli-microsoft365` or `msgcli` for M365, or `smtplib` for SMTP email.
