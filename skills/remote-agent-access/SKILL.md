---
name: remote-agent-access
description: >
  Phone access to AI agents via Telegram bot or terminal.
---

# Remote Agent Access

## When to use
- User wants to message their AI coding agent from a phone
- User asks for 'access from anywhere', 'chat from mobile'
- The official plugin isn't working or needs an always-on daemon

## Three modalities

### 1. Official plugin (when agent runs actively)
The coding agent ships a plugin that bridges messages via MCP. Requires the
agent to be running — plugin is an MCP server, not a daemon. When the session
ends, the plugin stops.

Setup: install plugin, configure bot token, set access control, start agent.

**Critical gotcha:** MCP health check "Connected" only confirms transport —
not that messages will be processed. Real test: message the bot and see if
anything happens.

### 2. Standalone bot (always-on, fallback)
Build a custom bot that calls the LLM API directly. Real daemon, no agent
session needed. No file/command access — just chat.

Pattern: `grammy` + LLM API (OpenRouter free tier, tunnel, etc).

### 3. Terminal access (9remote)
Full terminal on phone via cloudflared tunnel. Run commands, use agent
interactively.

## Verification before claiming "working"
1. Bot token works: `curl https://api.telegram.org/bot$TOKEN/getMe`
2. Access control set: `access.json` with user ID
3. LLM backend works: test API independently with curl
4. Process running: check `ps`, not just exit code
5. End-to-end: message bot from actual account, confirm reply

## Pitfalls
- MCP "Connected" ≠ messages flow. Always test end-to-end.
- Plugin when agent won't be running: won't work at 2am. Use standalone.
- grammy needs Bun. Without it: `ENOENT bun`. Install Bun first.
- cloudflared tunnel flaky: retry `9remote start`, check binary + network.
- Tunnel returning "API key required" for everything: backend likely down,
  not bot misconfigured. Verify backend listens before blaming bot.

## Standalone Claude Code Telegram bot (always-on fallback)

When Claude Code isn't running, the official Claude Code Telegram plugin MCP server is dead — no session = no plugin. For always-on Telegram access without an active agent session, build a standalone Bun + grammy bot that calls OpenRouter directly.

**Prerequisites:** Bun v1.4.2+ (the standalone bot needs Bun, not Node — the official Telegram plugin is an MCP server, the standalone bot is a separate thing built from scratch).

**Pattern:**

```typescript
// bot.ts — standalone Claude Code Telegram bot via OpenRouter
import { Bot } from "grammy";
import { request } from "./openrouter"; // your OpenRouter fetch wrapper

const bot = new Bot("BOT_TOKEN"); // from @BotFather

// Access control — only allow specific Telegram user IDs
const ALLOWED_IDS = ["701672095"]; // your Telegram ID
bot.use((ctx, next) => {
  if (!ALLOWED_IDS.includes(ctx.from.id.toString())) {
    return ctx.reply("Access denied.");
  }
  return next();
});

// On new message — call OpenRouter
bot.on("message", async (ctx) => {
  const userMsg = ctx.message.text;
  try {
    const reply = await request({
      model: "claude-sonnet-4-20250514",
      messages: [{ role: "user", content: userMsg }],
      max_tokens: 4096,
    });
    await ctx.reply(reply.choices[0].message.content);
  } catch (err) {
    await ctx.reply("Error: " + (err instanceof Error ? err.message : String(err)));
  }
});

bot.start();
```

**OpenRouter call pattern (OpenAI-compatible):**

```typescript
// openrouter.ts
export async function request(body: any) {
  const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.OPENROUTER_KEY}`,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`OpenRouter ${res.status}: ${text}`);
  }
  return res.json();
}
```

**Run as persistent process:**

```bash
# Install Bun if missing
curl -fsSL https://bun.sh/install | bash

# Install deps
bun add grammy

# Run in background
nohup bun bot.ts > bot.log 2>&1 &
# or use systemd for persistence
```

**Credentials needed:**
- Telegram bot token from @BotFather (e.g. `8583312503:...`)
- OpenRouter API key (free tier works — `sk-or-...`)
- Telegram user ID for access control (find via `@userinfobot` on Telegram)

**Pairing codes:** When pairing the bot to a Telegram account, Telegram shows pairing codes like `RGKZQTJS` or `4FTV4Z7Y` — these are one-time approval codes shown in the bot's first message to a new user. The user must approve (tap "Start" or the pairing button in Telegram UI), not type them into the bot.

**Important: standalone bot ≠ Claude Code plugin.** The standalone bot only does chat — no file access, no shell commands, no agent capabilities. It's a fallback for "message me from phone" when the full agent isn't running. For full agent access from phone, use 9remote (terminal access) instead.
