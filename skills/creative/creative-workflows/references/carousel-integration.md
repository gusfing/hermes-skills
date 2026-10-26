# Carousel Integration: Ian Xiaohei + Instagram Carousel Pipeline

## Overview
This reference documents the integration of Ian Xiaohei illustrations (hand-drawn, 16:9 white BG) into Instagram carousels (1080×1350, 4:5 dark mode) using the html-to-carousel export tool.

## Structure Mapping: Xiaohei Structure Types → Carousel Slides

| Carousel Slide | Purpose | Xiaohei Structure | Xiaohei Action | Reuse Strategy |
|----------------|---------|-------------------|----------------|----------------|
| 1 (Hook) | Bold claim + swipe cue | One Fish Many Uses | Carry core concept to multiple worktree folders | Source for slide 3 |
| 2 (Context) | Problem setup | Two Breakpoints | Pull decision lever / at breakpoint | Source for slide 4 |
| 3 (Value 1) | Core concept | One Fish Many Uses | Carry concept (reuse slide 1) | **Reuse slide 1 illustration** |
| 4 (Value 2) | Key feature | Two Breakpoints | Pull lever / operate machine (reuse slide 2) | **Reuse slide 2 illustration** |
| 5 (Value 3) | Parallel execution | Handoff Path | Operate 3 parallel conveyor belts | Unique |
| 6 (Value 4) | Cleanup/Git-native | Information Well | Filter code through funnel | Unique |
| 7 (CTA) | Save/follow | Trust Bridge | Connect/bridge elements | Can reuse 1-2 |

**Proven ratio:** 4 unique Xiaohei illustrations for 7 slides (slides 3 & 4 reuse 1 & 2).

## Prompt Templates for Carousel Slides

### Dark Mode Spot Illustrations (16:9, embedded in slides)
```
16:9 horizontal English article illustration, pure white background, black hand-drawn line art, thin wobbly lines, lots of empty white space (40-60% subject, 35%+ blank). Xiaohei (black solid creature, white dot eyes, thin legs, blank serious expression) as core action subject: [XIAOHEI_ACTION]. Sparse English handwritten annotations (max 5-8, 1-5 words each): [LABELS in red/orange/blue]. No titles, no PPT look, no commercial illustration, no cute cartoon, no gradients/shadows/texture. Weird, creative, clean, slightly unhinged product-sketch feel.
```

**For dark slide backgrounds:** Add "Xiaohei with thin white outline (2px) for contrast on dark backgrounds" to prompt.

### Full-Slide Background Illustrations (4:5 portrait, full bleed)
```
Instagram carousel slide [N] of 7. 1080x1350 portrait. Dark gradient from #0f172a to #312e81. Large bold white text: "[HEADLINE]". Subtitle: "[SUB]" in 28px opacity 0.7. Bottom: "Swipe →" in 26px opacity 0.5. Clean, modern, high contrast.
```

**Note:** Full-slide backgrounds use gradient + text, not Xiaohei. Xiaohei used as spot illustrations within slides.

## Accent Color System for Carousel

| Agent/Topic | Accent Hex | Usage |
|-------------|------------|-------|
| Claude Code | #818cf8 (purple) | Primary, OG, worktrees |
| Cursor | #22d3ee (cyan) | IDE-native, inline |
| Aider | #f472b6 (pink) | Terminal-first, Git |
| Codex | #fbbf24 (amber) | Cloud, async, PRs |
| OpenCode | #4ade80 (green) | Local, privacy, offline |
| Generic Red | #E60000 | Critical, CTA, highlights |
| Generic Blue | #818cf8 | Flow, automation, AI |

## HTML Carousel Template Requirements (for export-carousel.py)

### Mandatory Structure
```html
<div class="ig-frame">
  <div class="carousel-viewport">
    <div class="carousel-track">
      <div class="slide">Slide 1 content</div>
      <div class="slide">Slide 2 content</div>
      ...
      <div class="slide">Slide 7 content</div>
    </div>
  </div>
</div>
```

### Mandatory CSS Classes (dark mode)
```css
.slide {
  width: 420px; height: 525px;
  background: #0f172a; color: #fff;
  padding: 48px 40px;
  display: flex; flex-direction: column;
}
.headline { font-size: 34px; font-weight: 900; line-height: 1.05; letter-spacing: -1px; }
.body-text { font-size: 13px; line-height: 1.5; color: #cbd5e1; }
.hero-image { flex: 1; display: flex; justify-content: center; align-items: center; min-height: 180px; }
.hero-image img { max-width: 95%; max-height: 220px; object-fit: contain; }
.progress-bar { position: absolute; bottom: 0; left: 0; right: 0; padding: 12px 20px 16px; }
.pb-track { flex: 1; height: 2px; background: #1e293b; border-radius: 1px; overflow: hidden; }
.pb-fill { height: 100%; border-radius: 1px; background: #22d3ee; }
.slide-num-large { font-size: 100px; font-weight: 900; color: rgba(34,211,232,0.15); position: absolute; top: 40px; right: 40px; }
```

### Viewport & Scale
- Tool viewport: 420×525
- Scale factor: 1080/420 = 2.5714x
- Output: 1080×1350 (4:5)

## Export Tool: scripts/export-carousel.py

### Usage
```bash
python3 scripts/export-carousel.py carousel.html --output-dir slides_output
```

### Dependencies
```bash
# One-time setup
python3 -m ensurepip --upgrade
python3 -m pip install playwright
python3 -m playwright install chromium
```

### Common Errors & Fixes
| Error | Cause | Fix |
|-------|-------|-----|
| "Missing .ig-frame" | HTML missing wrapper | Add `<div class="ig-frame">` wrapping carousel |
| "Missing .carousel-viewport" | Structure wrong | Follow exact nesting: ig-frame > carousel-viewport > carousel-track > slide |
| "No slides found" | No .slide elements | Add `<div class="slide">` for each slide |
| Playwright not found | pip/venv issue | `python3 -m ensurepip --upgrade && pip install playwright` |
| Chromium missing | Not installed | `python3 -m playwright install chromium` |
| ARM64 fallback build | Oracle Linux ARM64 | Normal — works despite warning |

### Proven Working
- ARM64 Oracle Linux 9 (Playwright ubuntu24.04-arm64 fallback)
- 7 slides exported in ~30 seconds
- Output verified: `file` shows "PNG image data, 1080 x 1350, 8-bit/color RGB"

## Dashboard & Sharing via Cloudflare Tunnel

### Quick Tunnel (Ephemeral)
```bash
cd carousel-output
python3 -m http.server 8090 --bind 0.0.0.0 &
cloudflared tunnel --url http://127.0.0.1:8090
```
- URL: `https://<random-words>.trycloudflare.com`
- Rotates on process restart

### Named Tunnel (Permanent) — Future
```bash
cloudflared tunnel login
cloudflared tunnel create carousel-dashboard
cloudflared tunnel route dns carousel-dashboard carousel.yourdomain.com
cloudflared tunnel run carousel-dashboard
```

### Dashboard Features
- Grid of 7 cards with slide previews
- "Download PNG" button per slide
- "Download ZIP (all)" button
- "View HTML source" link
- Xiaohei illustration source strip
- White BG, red accent, high contrast

## Verification Checklist (Post-Export)

- [ ] All 7 slides exist in output directory
- [ ] `file *.png` confirms "1080 x 1350" for each
- [ ] Dark slides: text readable, Xiaohei visible (white outline on dark bg)
- [ ] Light illustrations: Xiaohei black lines on pure white
- [ ] ZIP contains all 7 PNGs + HTML source
- [ ] Tunnel serves PNGs: `Content-Type: image/png`, HTTP 200
- [ ] Dashboard renders all 7 cards with images
- [ ] Progress bar shows correct fraction (1/7 through 7/7)

## Session Examples

### Example 1: Claude Code Worktree Carousel
- Topic: Native Git Worktrees (`-w` flag)
- Slides: 7 (Hook, Context, Value×4, CTA)
- Xiaohei illustrations: 4 unique (parallel agents, lever, conveyor belts, funnel)
- Accent: #818cf8 (purple) for Claude Code
- Tunnel: https://paint-journalism-arctic-receptors.trycloudflare.com/

### Example 2: 7 AI Coding Agents Carousel
- Topic: Agent comparison (Claude Code, Cursor, Aider, Codex, OpenCode)
- Slides: 7 (Hook, 5 agents, CTA)
- Xiaohei illustrations: 2 unique (parallel agents, bugs) + reused
- Accents: per-agent color system
- Tunnel: https://knife-surrounded-too-maryland.trycloudflare.com/

## Pitfalls & Gotchas

1. **External image loading** — Tool waits for `networkidle` + 3s font wait. FAL.media URLs work directly. Increase `--font-wait-ms` for slow CDN.

2. **Server binding** — Must use `--bind 0.0.0.0` (not 127.0.0.1) for Cloudflare Tunnel to reach it.

3. **Quick tunnel rotation** — trycloudflare.com URLs change on every process restart. Save named tunnel for permanence.

4. **html-to-carousel exact structure** — `.ig-frame` > `.carousel-viewport` > `.carousel-track` > `.slide` is MANDATORY. No wrapper = hard error.

5. **ARM64 Chromium** — Playwright downloads ubuntu24.04-arm64 fallback (~300MB). Works but warns.

6. **Local vision models** — LLaVA GGUF requires model + mmproj. `llama-cpp-python` needs `clip_model_path`. Moondream-2B single-file GGUF not on HF. Quick path: use Nous `vision_analyze` with public URLs.

7. **Reuse strategy** — 4 unique Xiaohei illustrations for 7 slides. Slides 3&4 reuse 1&2. Proven faster, more coherent.

8. **Progress bar math** — Slide N: `width: N/7 * 100%` (14.28%, 28.57%, 42.85%, 57.14%, 71.42%, 85.71%, 100%)

## File Structure in Skill

```
creative/creative-workflows/
├── SKILL.md
├── scripts/
│   └── export-carousel.py          # Standalone Playwright exporter
├── templates/
│   ├── carousel-template.html      # For export tool (420x525 viewport)
│   └── instagram-carousel-1080x1350.html  # For manual rendering
└── references/
    ├── carousel-integration.md     # THIS FILE
    ├── claude-code-carousel-prompts.md
    └── dashboard-sharing.md
```