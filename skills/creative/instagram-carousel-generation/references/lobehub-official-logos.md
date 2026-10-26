# LobeHub Official Brand Logos (from lobehub/lobe-icons)

## Verified Logo URLs (raw.githubusercontent.com)

All logos are 640x640 PNG, 8-bit colormap, transparent background.
Use directly in carousel HTML via absolute URLs.

| Brand | File | URL |
|-------|------|-----|
| **Claude Code** | `claudecode.png` | `https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/claudecode.png` |
| **Cursor** | `cursor.png` | `https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/cursor.png` |
| **Codex** | `codex.png` | `https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/codex.png` |
| **OpenCode** | `opencode.png` | `https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/opencode.png` |
| **Cline (Aider proxy)** | `cline.png` | `https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/cline.png` |

## Dark Mode Variants

| Brand | Dark Mode File | URL |
|-------|----------------|-----|
| **Claude Code** | `claudecode.png` (dark) | `https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/dark/claudecode.png` |
| **Cursor** | `cursor.png` (dark) | `https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/dark/cursor.png` |
| **Codex** | `codex.png` (dark) | `https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/dark/codex.png` |
| **OpenCode** | `opencode.png` (dark) | `https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/dark/opencode.png` |

## Usage in Carousel HTML

```html
<!-- Hero image on slide -->
<img src="https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/claudecode.png" alt="Claude Code logo" style="max-width:180px;max-height:180px;">

<!-- Logo row on hook slide -->
<div class="logo-row">
  <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/claudecode.png" alt="Claude Code" style="width:60px;height:60px;">
  <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/cursor.png" alt="Cursor" style="width:60px;height:60px;">
  <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/cline.png" alt="Aider" style="width:60px;height:60px;">
  <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/codex.png" alt="Codex" style="width:60px;height:60px;">
  <img src="https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/opencode.png" alt="OpenCode" style="width:60px;height:60px;">
</div>
```

## Notes

- Aider doesn't have a dedicated logo in lobe-icons; use `cline.png` (closest terminal AI tool) as proxy
- Logos are served via GitHub raw CDN — fast, reliable, no auth needed
- All logos use consistent style (light/dark variants available)
- Check `https://github.com/lobehub/lobe-icons/tree/master/packages/static-png/light` for updates