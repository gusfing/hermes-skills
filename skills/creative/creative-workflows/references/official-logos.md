# Official Brand Logos — LobeHub Source

**Source:** `github.com/lobehub/lobe-icons` → `packages/static-png/light/`
**Format:** 640x640 PNG, transparent background, official brand assets
**CDN:** `https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/<filename>.png`

## Available Logos (verified)

| Brand | Filename | URL | Use Case |
|-------|----------|-----|----------|
| Claude Code | `claudecode.png` | `.../claudecode.png` | Primary agent branding |
| Cursor | `cursor.png` | `.../cursor.png` | IDE-native agent |
| Codex (OpenAI) | `codex.png` | `.../codex.png` | Cloud agents |
| OpenCode | `opencode.png` | `.../opencode.png` | Local-first agent |
| Cline | `cline.png` | `.../cline.png` | Terminal-first (Aider proxy) |
| GitHub Copilot | `githubcopilot.png` | `.../githubcopilot.png` | VS Code agent |
| Windsurf | `windsurf.png` | `.../windsurf.png` | Cascade agent |
| Devin | `devin-color.png` | `.../devin-color.png` | Autonomous agent |
| Gemino CLI | `geminicli.png` | `.../geminicli.png` | Google CLI agent |

## Download Commands

```bash
mkdir -p agent-logos
cd agent-logos
# Core 5 for AI coding agents carousel
curl -sL "https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/claudecode.png" -o claude.png
curl -sL "https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/cursor.png" -o cursor.png
curl -sL "https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/cline.png" -o aider.png
curl -sL "https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/codex.png" -o codex.png
curl -sL "https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/opencode.png" -o opencode.png
```

## Carousel Integration

**Hook slide logo row:**
```html
<div class="logo-row">
  <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/claudecode.png" alt="Claude Code">
  <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/cursor.png" alt="Cursor">
  <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/cline.png" alt="Aider">
  <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/codex.png" alt="Codex">
  <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/opencode.png" alt="OpenCode">
</div>
```

**Per-slide hero logo:**
```html
<div class="hero-image">
  <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/claudecode.png" alt="Claude Code logo">
</div>
```

**CSS for logos:**
```css
.logo-row {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 16px;
}
.logo-row img {
  width: 60px;
  height: 60px;
  object-fit: contain;
}
.hero-image img {
  max-width: 180px;
  max-height: 180px;
  width: auto;
  height: auto;
  object-fit: contain;
}
```

## Notes

- All logos are official brand assets maintained by the respective companies via LobeHub
- Transparent background works on both dark and light carousel backgrounds
- 640x640 source scales cleanly to any display size
- No attribution required for editorial/educational use
- If a logo is missing, check `packages/static-png/dark/` for dark-mode variants