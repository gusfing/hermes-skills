---
name: claude-code-telegram
description: >
  Set up Claude Code's official Telegram plugin on a remote Linux server.
  Covers plugin install, Bun aarch64 dependency, bot token config via .env,
  MCP server verification, and pairing flow.
---

# Claude Code Telegram Plugin Setup

## When to use

- User wants to chat with Claude Code from Telegram
- User says "install claude code telegram skill" or "claude code telegram"
- Claude Code is already installed and authenticated on the server

## What it is

Claude Code has an **official Telegram plugin** (`telegram@claude-plugins-official`) — separate from OpenClaw's Telegram channel. It bridges messages to a Telegram bot via an MCP server.

- Plugin: `telegram@claude-plugins-official` v0.0.7+
- Includes: MCP server (`telegram`), skills (`access`, `configure`)
- Always-on token cost: ~118 tok per session
- Config: `~/.claude/settings.json` → `enabledPlugins["telegram@claude-plugins-official"] = true`

## Install

```bash
claude plugin install telegram@claude-plugins-official
claude plugin enable telegram@claude-plugins-official  # if not auto-enabled
```

## Bun dependency (aarch64 / ARM Linux) — CRITICAL

The Telegram plugin's MCP server runs `server.ts` via Bun. On aarch64 Linux, the standard installer (`curl -fsSL https://bun.sh/install | bash`) can **fail silently** — curl returns an error, no binary is produced, Bun ends up missing from PATH.

**Symptom:** `claude mcp list` shows:
```
plugin:telegram:telegram: bun run ... - ✘ Failed to connect — ENOENT: Executable not found in $PATH: "bun"
```

**Workaround — download the static zip directly:**

```bash
cd /tmp
curl -fsSL -o bun.zip "https://github.com/oven-sh/bun/releases/latest/download/bun-linux-aarch64.zip"
unzip -o bun.zip
mkdir -p ~/.bun/bin
cp bun-linux-aarch64/bun ~/.bun/bin/bun
chmod +x ~/.bun/bin/bun
export PATH="$HOME/.bun/bin:$PATH"
bun --version  # verify
```

The static binary is self-contained. Add `~/.bun/bin` to PATH permanently (`~/.bashrc` or `~/.bash_profile`) so Claude Code's MCP server can find it on every launch.

**Check the URL:** the correct filename is `bun-linux-aarch64.zip` (not `bun-linux-aarch64-static.zip` or versioned paths like `bun-v1.2.10/bun-linux-aarch64-static.zip` which 404).

## Configure bot token

The MCP server reads the token from a `.env` file — **not** from Claude Code settings or CLI flags:

```bash
mkdir -p ~/.claude/channels/telegram
echo 'TELEGRAM_BOT_TOKEN=123456789:ABCdef...' > ~/.claude/channels/telegram/.env
```

Get the token from **@BotFather** on Telegram:
1. Message @BotFather
2. Send `/newbot`
3. Name (display name, e.g. "Claude Code")
4. Username (must be unique, e.g. `claude_code_kawaki`)
5. Copy the token it returns

The token format is `NNNNNNNNN:AAH...` — the numeric prefix is the BotFather bot ID.

## Verify

```bash
claude mcp list
```

Expected output:
```
plugin:telegram:telegram: bun run --cwd ... --shell=bun --silent start - ✔ Connected
```

If it shows `✘ Failed to connect — ENOENT: "bun"` → Bun not on PATH (see Bun section above).

If it shows `✔ Connected` → MCP server is running and can read the token.

## Pairing

1. **Message your bot on Telegram** — send any message
2. Bot replies with: "Pairing code: XYZ12345. Run: ..."
3. **Approve the pairing** inside Claude Code:
   ```
   /telegram:access approve XYZ12345
   ```
   Or use the `access` skill.
4. After approval, messages sent to the bot are routed through Claude Code and replies come back via Telegram.

## Test

Send a message to the bot on Telegram. If paired, Claude Code should respond.

## Notes

- The bot token from an old OpenClaw setup may still work if the bot wasn't deleted — check @BotFather to see existing bots. If the bot was tied to OpenClaw and OpenClaw was deleted, the bot may still exist (Telegram owns the bot, not OpenClaw).
- Claude Code's Telegram plugin uses the model/config that Claude Code itself is configured with — it does NOT have its own model settings. If Claude Code uses a tunnel endpoint, Telegram messages go through that tunnel too.
- The plugin's MCP server starts automatically when Claude Code launches — no manual `bun server.ts` needed in normal use. The manual start is only for debugging.
