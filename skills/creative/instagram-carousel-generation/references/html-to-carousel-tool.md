# html-to-carousel Tool Reference

## Tool Source
- GitHub: https://github.com/Hanseldemulcent167/html-to-Instagram-carousel
- Installed at: `/tmp/html-to-carousel/`
- Dependencies: Python 3.11+, Playwright, Chromium

## Installation
```bash
cd /tmp/html-to-carousel
pip3 install -r requirements.txt
python3 -m playwright install chromium
```

## Usage
```bash
python3 main.py /path/to/carousel.html --output-dir /path/to/output [--font-wait-ms 3000]
```

## Required HTML Structure (NON-NEGOTIABLE)

The tool expects EXACT CSS classes and structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Carousel Title</title>
  <style>...</style>
</head>
<body>
  <div class="ig-frame">
    <div class="carousel-viewport">
      <div class="carousel-track">
        <div class="slide">Slide 1 content</div>
        <div class="slide">Slide 2 content</div>
        <!-- ... up to 7+ slides -->
      </div>
    </div>
  </div>
</body>
</html>
```

### Required Classes (must match exactly)

| Class | Purpose |
|-------|---------|
| `.ig-frame` | Outer wrapper, 420px wide |
| `.carousel-viewport` | Viewport, 420x525, overflow hidden |
| `.carousel-track` | Flex container, width = 100% * slide count |
| `.slide` | Each slide, 420x525, flex-shrink: 0 |

### Auto-hidden Elements (tool removes from screenshots)

- `.ig-header`
- `.ig-dots`
- `.ig-actions`
- `.ig-caption`
- `.swipe-arrow`
- `.logo-lockup`

### Progress Bar (REQUIRED for slide numbering)

```html
<div class="progress-bar">
  <div class="pb-track">
    <div class="pb-fill" style="width: 14.28%;"></div>
  </div>
  <span class="pb-label">01/07</span>
</div>
```

Width percentages: 14.28%, 28.57%, 42.85%, 57.14%, 71.42%, 85.71%, 100%

## Output

- 7 PNG files at 1080x1350 (420x525 * 2.57 device_scale_factor)
- Named: `{input_stem}_1.png` through `{input_stem}_7.png`
- 8-bit RGB, non-interlaced

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Missing .ig-frame` | HTML missing required wrapper | Add `<div class="ig-frame">` |
| `Missing .carousel-viewport` | HTML missing viewport | Add `<div class="carousel-viewport">` |
| `Missing .carousel-track` | HTML missing track | Add `<div class="carousel-track">` |
| `No slides found` | Slides don't have `.slide` class | Add `class="slide"` to each slide |
| Font rendering issues | Fonts not loaded | Increase `--font-wait-ms` |

## Viewport Settings (in main.py)

```python
VIEW_W = 420
VIEW_H = 525
SCALE = 1080 / 420  # = 2.5714...
DEFAULT_FONT_WAIT_MS = 3000
```

## Export Script Template

```bash
#!/bin/bash
# scripts/export-carousel.sh
set -e
INPUT_HTML="${1:-carousel.html}"
OUTPUT_DIR="${2:-carousel-output}"
cd /tmp/html-to-carousel
python3 main.py "$INPUT_HTML" --output-dir "$OUTPUT_DIR"
echo "Exported to: $OUTPUT_DIR"
```