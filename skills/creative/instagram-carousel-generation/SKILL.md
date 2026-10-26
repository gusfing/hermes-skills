---
name: instagram-carousel-generation
description: "Create Instagram carousels via html-to-carousel tool."
---
# Instagram Carousel Generation

## When to Use
Create Instagram carousels (1080x1350, 4:5) for technical content. Covers design, HTML template, export via html-to-carousel tool, illustration generation, and public deployment.

## Core Workflow

### 1. Design System (User-Preferred)
- **Background**: White (`#fff`)
- **Accent**: `#E60000` (red) — headlines, progress bar, slide numbers
- **Text**: `#111` headings, `#333` body, `#666` subheadings, `#999` hints
- **Typography**: System font stack, weights 900/700/400
- **Slide numbers**: Large (100px) watermark at top-right, 6% opacity red
- **Progress bar**: Bottom, red fill, label "XX/07"
- **Swipe hint**: "Swipe →" bottom center on slide 1

### 2. 7-Slide Framework (from social-media-carousel skill)
| Slide | Purpose | Content |
|-------|---------|---------|
| 1 | Hook | Bold claim + swipe cue |
| 2 | Context | Problem setup |
| 3-6 | Value | One point per slide, numbered |
| 7 | CTA | Save + follow |

### 3. HTML Template Structure (CRITICAL for html-to-carousel)
The export tool requires EXACT CSS classes:
```html
<div class="ig-frame">
  <div class="carousel-viewport">
    <div class="carousel-track">
      <div class="slide">...</div>  <!-- 7 slides -->
    </div>
  </div>
</div>
```
- Viewport: 420x525 (scaled 2.57x to 1080x1350)
- Each `.slide`: 420x525, flex column, padding 48px 40px
- Tool hides `.ig-header`, `.ig-dots`, `.ig-actions`, `.ig-caption` automatically
- Tool requires `.ig-frame`, `.carousel-viewport`, `.carousel-track`, `.slide`

### 4. Ian Xiaohei Illustrations
Use `ian-xiaohei-illustrations` skill. Prompt pattern:
```
16:9 horizontal English article illustration, pure white background, black hand-drawn line art, thin wobbly lines, lots of empty white space (40-60% subject, 35%+ blank). Xiaohei (black solid creature with two dot eyes) [ACTION]. Sparse annotations: red label "[X]", blue label "[Y]", orange label "[Z]". Hand-drawn, sketchy, clean, weird but clear. No title, no gradients, no shadows.
```
Structures: One Fish Many Uses, Two Breakpoints, Handoff Path, Information Well.

### 5. Export
```bash
cd /tmp/html-to-carousel
python3 main.py /path/to/carousel.html --output-dir /path/to/output
```
Output: 7 PNGs at 1080x1350, 8-bit RGB.

### 6. Deploy (Quick Tunnel)
```bash
cd /path/to/output
python3 -m http.server 8090 --bind 0.0.0.0 &
cloudflared tunnel --url http://127.0.0.1:8090
```
URL format: `https://<random>.trycloudflare.com/` — changes on restart.

## Pitfalls
- Do not use custom HTML structure — tool expects exact classes above
- Do not use dark mode unless user requests — default is white/red
- Do not forget `.progress-bar` with `.pb-fill` width percentages (14.28%, 28.57%, etc.)
- Do not use aspect ratios other than 4:5 for Instagram feed
- Test export locally before deploying
- Zip all PNGs + HTML source for delivery
- **Cloudflare quick tunnels change URL on restart** — use stable hosting (S3, Netlify, Vercel, GitHub Pages) for production
- **Agent Reach is read-only** — it cannot post to Buffer or any platform. Use direct Buffer GraphQL API for posting carousels.
- **LobeHub logos** — use `https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-png/light/<logo>.png` for reliable CDN delivery
- **YouTube requires JS runtime** — configure `yt-dlp` with `--js-runtimes node` in `~/.config/yt-dlp/config` for subtitle extraction

## Related Skills
- `ian-xiaohei-illustrations` — for custom illustrations
- `social-media-carousel` (hub) — 7-slide framework reference

## References
- `references/xiaohei-prompt-patterns.md` — Prompt templates for both carousels (Claude Code worktree + AI Agents)
- `references/lobehub-official-logos.md` — Verified logo URLs from lobehub/lobe-icons
- `references/buffer-api-carousel-posting.md` — Buffer GraphQL API for scheduling carousel posts
- `references/html-to-carousel-tool.md` — Export tool reference and required HTML structure
- `references/agent-reach-setup.md` — Agent Reach installation and channel config for research
- `references/session-notes.md` — Session-specific findings: 9router empty catalog, html-to-carousel install issues

## Notes
- **Terse responses preferred:** Agent reached via CLI. Markdown does NOT render, so use plain text. User prefers direct answers over elaborate explanations.
- **9router caveat:** Empty catalog `=>` configured provider NOT working. Check `providerConnections` table in `~/.9router/db/data.sqlite`:
  - OpenRouter: Returns 402 when credits exhausted - visit https://openrouter.ai/settings/credits to add funds
  - Any provider: Returns 401 for bad API keys - regenerate/replace credentials in 9Router dashboard
  - No providers: `providerNodes` table empty - need to add credentials via dashboard
- **html-to-carousel fallback:** When 9router unavailable, create HTML manually and export locally via html-to-carousel tool (requires installation at /tmp/html-to-carousel)