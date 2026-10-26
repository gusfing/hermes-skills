---
name: creative-workflows
description: End-to-end creative pipelines for carousels.
---
# Creative Workflows

Class-level umbrella for multi-step creative pipelines: Instagram/LinkedIn carousels, article illustrations, HTML-to-image export.

## Sub-skills
- `ian-xiaohei-illustrations` - Ian-style Xiaohei article illustrations (hand-drawn, white, 16:9)
- `social-media-carousel` - 7-slide framework for Instagram/LinkedIn/X (inference.sh)
- HTML-to-carousel export via Playwright (1080x1350 PNGs)

## Carousel Pipeline (End-to-End)

### 1. Plan (7-Slide Framework)
| Slide | Purpose | Structure Type (Xiaohei) |
|-------|---------|--------------------------|
| 1 | Hook | One Fish Many Uses / Bold Claim |
| 2 | Context | Two Breakpoints / Problem |
| 3 | Value 1 | One Fish Many Uses (reuse) |
| 4 | Value 2 | Two Breakpoints (reuse) |
| 5 | Value 3 | Handoff Path / Sort by Purpose |
| 6 | Value 4 | Information Well / Idea Press |
| 7 | CTA | Trust Bridge |

### 2. Generate Illustrations
Use `ian-xiaohei-illustrations` skill -> `image_gen` with 16:9 prompts.
- Pure white BG, black hand-drawn lines, sparse red/orange/blue annotations
- Xiaohei as core action subject (never decorative)
- Max 5-8 annotations, 1-5 words each
- **Reuse strategy:** Slides 3 & 4 reuse illustrations from slides 1 & 2 for visual consistency. 4 unique images for 7 slides.

### 3. Build HTML Carousel
Template: `templates/carousel-template.html` — plug-and-play 7-slide carousel (1080x1350).
Variables: `{{TITLE}}`, `{{HANDLE}}`, `{{SLIDE{N}_HEADLINE}}`, `{{SLIDE{N}_SUB}}`, `{{SLIDE{N}_BODY}}`, `{{SLIDE{N}_IMG}}`, `{{SLIDE{N}_ALT}}`, `{{SLIDE{N}_CTA}}`, `{{SLIDE{N}_FOOTER}}`.
- 1080x1350 (4:5) for Instagram max feed real estate
- `.ig-frame` wrapper required for Playwright exporter
- Flex track with 7 slides, progress dots, swipe hint
- Supports inline `<code class="inline">` and `<code class="block">` for code snippets

### 4. Export PNGs
Use the standalone exporter (no external repo):
```bash
python3 scripts/export-carousel.py carousel.html --output-dir slides_output
```
Requires: `playwright` + `chromium` (`python3 -m playwright install chromium`).
- Script: `scripts/export-carousel.py` — robust slide detection, clip-based screenshots, error messages for missing `.ig-frame` or `.slide` elements.
- Auto-installs Playwright + Chromium if missing.
- **Proven working:** Exported 7 slides at 1080x1350 in ~30s on ARM64 Oracle Linux (Playwright fallback build)

### 5. Dashboard & Sharing
Serve exported PNGs + HTML locally and expose via Cloudflare Tunnel:
```bash
cd carousel-output
python3 -m http.server 8090 --bind 0.0.0.0 &
cloudflared tunnel --url http://127.0.0.1:8090
```
Access at the trycloudflare.com URL. Quick tunnels rotate on restart — use named tunnel for permanence.
**Working example from session:** 7 slides exported, dashboard served at https://paint-journalism-arctic-receptors.trycloudflare.com/ with ZIP download, individual PNGs, and HTML source.

## Related Skills
- `social-media-carousel` (hub) — inference.sh 7-slide framework, platform specs, swipe psychology. Install: `npx -y skills add inferen-sh/skills --skill social-media-carousel --agent claude-code`
- `ian-xiaohei-illustrations` — hand-drawn Xiaohei article illustrations (16:9, white BG)

## Working Prompts Reference
See `references/claude-code-carousel-prompts.md` for Xiaohei prompts (Claude Code worktree + 7 AI Agents carousels).

## Official Logos Reference
See `references/official-logos.md` for LobeHub-sourced brand logos (Claude Code, Cursor, Codex, OpenCode, Cline/Aider, etc.). 640x640 PNG, transparent BG, official assets.

## Dashboard & Sharing Setup
See `references/dashboard-sharing.md` for quick tunnel, named tunnel, and dashboard structure.

## Templates
- `templates/carousel-template.html` — **Use this with export-carousel.py** (420×525 viewport, scaled 2.5714x to 1080×1350). Matches html-to-carousel tool structure exactly.
- `templates/instagram-carousel-1080x1350.html` — Direct 1080×1350 template (for manual browser rendering, NOT for export tool).

## Pitfalls
- **Missing `.ig-frame`** -> Playwright exporter fails with "Missing .ig-frame in the HTML file"
- **No pip in venv** -> Run `python3 -m ensurepip --upgrade` first
- **Chromium not installed** -> `python3 -m playwright install chromium` (downloads ~300MB)
- **ARM64 fallback** -> Playwright downloads ubuntu24.04-arm64 builds (works but warns)
- **Font wait** --font-wait-ms 3000 default; increase for custom fonts
- **Server binding** -> Use `--bind 0.0.0.0` (not 127.0.0.1) for Cloudflare Tunnel to reach it
- **Local vision models** -> LLaVA GGUF requires both model + mmproj file; `llama-cpp-python` needs `clip_model_path` parameter. Moondream-2B single-file GGUF simpler but not on HF as GGUF. Quick path: use Nous subscription `vision_analyze` tool with public URLs.
- **Quick tunnel rotation** -> trycloudflare.com URLs change on process restart; use named tunnel for permanence
- **html-to-carousel tool requires exact structure** -> Must have `.ig-frame` > `.carousel-viewport` > `.carousel-track` > `.slide` elements. No `.ig-frame` = hard error. Viewport is 420×525 scaled by 2.5714x to 1080×1350. The tool hides Instagram chrome (header, dots, actions, caption) and screenshots clipped to viewport.
- **External image loading** -> Wait for `networkidle` + 3s font wait minimum. FAL.media URLs work directly in `<img src>`.
- **Reuse strategy for Xiaohei** -> 4 unique illustrations for 7 slides: slides 3 & 4 reuse slides 1 & 2 illustrations for visual consistency. Proven faster and more coherent.