---
name: sales-outreach
description: "Build outbound sales kits for booking meetings."
version: 1.0.0
metadata:
  hermes:
    tags: [sales, outreach, leads, meetings, cold-email, linkedin, templates]
    category: productivity
---

# Sales Outreach

## Trigger
User says variants of: "setup sales", "get clients", "outreach kit", "cold email templates", "book meetings", "lead generation", "I need clients", or names a business/venture and asks for sales setup.

## Contract
- Deliver a complete, ready-to-use outreach kit in a dedicated workspace folder
- Include templates, sequences, tracking, and notification setup
- Validate every deliverable is a real file, not a plan
- Keep tone direct, action-first, no AI-fluff

## Procedure

### 1. Scout existing infrastructure
Before building, check:
- Existing email tools installed (`himalaya`, `msmtp`, `sendmail`, `python3 smtplib`)
- Existing email skills in `~/.hermes/skills/email/`
- Available notification channels (Telegram bot token, webhook, etc.)
- Current workspace structure to avoid overwriting

### 2. Build the kit skeleton
Create a dedicated folder, e.g. `kawaki-sales-kit/` with:
```
templates/
sequences/
tracking/
email/
telegram/
README.md
```

### 3. Write templates (keep them short)
Templates must be 4-6 lines for email, 3-4 sentences for LinkedIn.
Include variables in `{{var}}` format for personalization.
Always include a clear CTA: "Are you open to a 15-min call this week?"

Required templates:
- `email-cold-v1.md` — cold outreach
- `linkedin-cold-v1.md` — 3 options (direct, value-first, mutual connection)
- `call-script.md` — opening, pain discovery, value pitch, close
- `proposal-v1.md` — one-page with scope, timeline, investment
- `followup-v1.md` — 4 scenarios (24h, 3d, 7d, no-show, rejection)

### 4. Write sequences
Create 3/5/7-touch sequences with:
- Day number
- Channel
- Template file
- Goal
- Exit criteria

Exit criteria must be explicit:
- Booked meeting → move to pipeline
- N touches no reply → nurture list, pause 30 days
- Explicit no → archive, don't follow up

### 5. Build tracking
- `tracking/lead-tracker.csv` — columns: id, company, contact_name, contact_title, email, linkedin, source, signal, pain_point, sequence, last_touch_date, last_touch_channel, next_touch_date, status, notes
- `tracking/pipeline.md` — Hot/Warm/Cold/Won/Lost tables
- `tracking/kpi-dashboard.md` — weekly metrics table + conversion benchmarks

### 6. Setup notification channel
Evaluate available channels in this order:
1. **Telegram** — if user provides a bot token, build a notifier script and fetch chat_id via `getUpdates`
2. **Himalaya CLI** — if user has himalaya configured, use for both sending and IMAP reply polling
3. **Raw SMTP** — fallback if no other channel is available

For Telegram:
- Create `telegram/telegram_notifier.py` with `--get-chat-id` and `--message` modes
- Create `telegram/config.yaml` with `chat_id` placeholder
- Test by asking user to message the bot first, then fetch updates

For email sending:
- Build `email/send_email.py` supporting single and CSV batch sends
- Create `email/config.yaml` with SMTP placeholders
- Include provider notes for Gmail, Outlook, custom SMTP

### 7. Wire Telegram as primary sales alert channel
When a Telegram bot token and chat_id are available:
- Prefer `hermes send --to telegram:<chat_id>` for instant alerts; it bypasses gateway and talks to Bot API directly
- If gateway is running, set `TELEGRAM_BOT_TOKEN` in the gateway service env and use `platforms.telegram.token` in config; do NOT use `platforms.telegram.bot_token` — it is silently ignored
- After alerts work, offer: meeting alerts, reply notifications, daily KPI summaries

### 8. Test and validate
- Run syntax checks on all scripts
- Test template rendering with sample variables
- Verify tracking files are valid CSV/Markdown
- Do a dry-run send to the user's own address first

## Pitfalls
- Don't use AgentMail for business outreach — `@agentmail.to` domain hurts deliverability and trust
- Don't hardcode bot tokens or credentials in memory or shared logs
- Don't send without explicit user confirmation of provider and from-address
- Don't create more than 3 sequence variants — user will pick one and stick with it
- Don't build web scrapers unless user asks — start with manual CSV entry

## Support Files
- `templates/email-cold-v1.md` — starter cold email template
- `templates/linkedin-cold-v1.md` — starter LinkedIn message templates
- `templates/call-script.md` — starter call/meeting script
- `templates/proposal-v1.md` — starter proposal template
- `templates/followup-v1.md` — starter follow-up templates
- `sequences/3touch-sequence.md` — quick close sequence
- `sequences/5touch-sequence.md` — nurture + close sequence
- `sequences/7touch-sequence.md` — full nurture sequence
- `tracking/lead-tracker.csv` — lead tracker template
- `tracking/pipeline.md` — pipeline board template
- `tracking/kpi-dashboard.md` — KPI dashboard template
- `references/notification-channels.md` — comparison of Telegram vs Himalaya vs SMTP for outreach
