# Telegram Gateway Setup Notes

## Verified workflow
- User provides bot token + chat_id
- Preferred send path: `hermes send --to telegram:<chat_id> "message"`
- This does NOT require gateway; it uses Bot API directly

## Gateway wiring
- Gateway service file: `~/.config/systemd/user/hermes-gateway.service`
- Add `TELEGRAM_BOT_TOKEN` as an `Environment=` line in the service file
- Restart: `systemctl --user daemon-reload && systemctl --user restart hermes-gateway`
- Gateway status: `hermes gateway status`

## Config.yaml gotchas
- Use `platforms.telegram.token`, not `bot_token`
- `bot_token` is silently ignored by the Telegram adapter
- Home channel can be set via env/config:
  - `TELEGRAM_HOME_CHANNEL=<chat_id>`
  - `TELEGRAM_HOME_CHANNEL_NAME=<name>`
- If gateway health still shows "No bot token configured", verify the service env contains `TELEGRAM_BOT_TOKEN`

## Debugging
- Logs: `journalctl --user -u hermes-gateway -n 50 --no-pager`
- Common error: `[Telegram] No bot token configured` means token not in process env
- Check process env: `tr '\0' '\n' < /proc/$(systemctl --user show -p MainPID --value hermes-gateway)/environ | grep TELEGRAM`
