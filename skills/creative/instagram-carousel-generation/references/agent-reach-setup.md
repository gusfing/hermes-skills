# Agent Reach Setup for Social Media Research (Complete)

## Purpose
Agent Reach gives AI agents internet reading capability across 15 platforms. Use for researching carousel topics, finding trends, reading competitor posts, etc.

**Critical**: Agent Reach is **read-only** — it cannot post to Buffer, Instagram, X, LinkedIn, etc. It only fetches content.

## Installation (One-Time)
```bash
git clone https://github.com/Panniantong/Agent-Reach /home/opc/Agent-Reach
cd /home/opc/Agent-Reach
pip3 install -e .
```

## Dependencies Installed This Session
```bash
pip3 install yt-dlp[default] twitter-cli rdt-cli bilibili-cli gh-cli ffmpeg-python
# Also needed: pip3 install loguru rich pyyaml feedparser python-dotenv requests
```

## Channel Status After Setup

| Platform | Status | Backend | Config Needed |
|----------|--------|---------|---------------|
| YouTube | ✅ ok | yt-dlp | `--js-runtimes node` in `~/.config/yt-dlp/config` |
| Bilibili | ✅ ok | bili-cli | None |
| V2EX | ✅ ok | Public API | None |
| RSS | ✅ ok | feedparser | None |
| Web (any page) | ✅ ok | Jina Reader | None |
| GitHub | ⚠️ warn | gh CLI | `gh auth login` |
| Twitter | ⚠️ warn | twitter-cli | `agent-reach configure twitter-cookies` |
| Reddit | ⚠️ warn | rdt-cli | Cookie-Editor export to `~/.config/rdt-cli/credential.json` |
| Instagram | ❌ off | OpenCLI | `pipx install opencli` + Chrome login |
| Facebook | ❌ off | OpenCLI | Same as Instagram |
| Xiaohongshu | ❌ off | OpenCLI | Same as Instagram |
| LinkedIn | ❌ off | mcp-server-linkedin | `uvx mcp-server-linkedin@latest --login` + mcporter |
| Exa Search | ❌ off | mcporter | `npm install -g mcporter` + Exa MCP |

## Quick Commands

```bash
# Check status
agent-reach doctor --json

# Configure cookies (run after Cookie-Editor export)
agent-reach configure twitter-cookies
agent-reach configure xhs-cookies

# Interactive setup
agent-reach setup

# One-shot install
agent-reach install --env=auto
```

## YouTube Subtitle Extraction (Working)
```bash
yt-dlp --write-sub --write-auto-sub --skip-download -o "/tmp/%(id)s" "URL"
```

## Web Page Reading (Working)
```bash
curl -s "https://r.jina.ai/URL"
```

## Bilibili Search (Working)
```bash
bili search "query" --type video -n 5
```

## V2EX Hot Topics (Working)
```bash
curl -s "https://www.v2ex.com/api/topics/hot.json" -H "User-Agent: agent-reach/1.0"
```

## Notes
- **OpenCLI failed to install via pipx** (pkg_resources build error) — use `pip3 install opencli` in venv if needed
- **Instagram/Facebook/Xiaohongshu** need OpenCLI + Chrome login session
- **Buffer posting** — use direct GraphQL API (see buffer-api-carousel-posting.md), Agent Reach cannot do this
- All installed tools are in `/home/opc/.hermes/hermes-agent/venv/bin/`
- **YouTube requires JS runtime** — configure `yt-dlp` with `--js-runtimes node` in `~/.config/yt-dlp/config` for subtitle extraction