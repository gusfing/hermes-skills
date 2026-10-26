# Notification Channels for Sales Outreach

## Telegram
- Best for: instant alerts, daily KPI summaries, meeting reminders
- Setup: bot token from @BotFather, fetch chat_id via `getUpdates`
- Pros: real-time, mobile-native, no email deliverability concerns
- Cons: requires user to message bot first to get chat_id
- Use when: user provides bot token or wants instant notifications

## Himalaya CLI
- Best for: sending + reading replies in one place
- Setup: `himalaya account configure` with IMAP/SMTP credentials
- Pros: uses real email domain, reads replies for lead tracking
- Cons: requires himalaya installed and configured
- Use when: himalaya is installed and user wants unified send/receive

## Raw SMTP (Python smtplib)
- Best for: simple batch sends when no other tool is available
- Setup: SMTP host, port, user, app password in config
- Pros: works everywhere Python runs, no extra dependencies
- Cons: no built-in reply tracking, no read receipts
- Use when: no himalaya, no Telegram, or user prefers minimal setup

## Decision tree
1. User provides Telegram bot token → use Telegram for notifications + raw SMTP for sending
2. Himalaya installed and configured → use Himalaya for both sending and IMAP polling
3. Otherwise → use raw SMTP with config.yaml placeholders

## AgentMail (do not use for business outreach)
- Free tier: 3 inboxes, 3000 emails/month
- Domain: `@agentmail.to` on free tier
- Why avoid: low trust, spam-filter risk, not your brand domain
- Use only for: testing, signup verification, agent-to-agent communication
