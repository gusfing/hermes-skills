#!/usr/bin/env python
"""Render a post card from a hook line. HTML -> headless Chromium -> PNG.

Exact text, deterministic output, no image-generation API. Use this for any
card where the words are the content - a diffusion model garbles them.

  usage: make_card.py --text "Delete code." --out card.png [--accent #38bdf8]
       make_card.py --slot 01 --day 2026-10-06 --out card.png
"""
import argparse
import html
import sys
from pathlib import Path

ROOT = Path("/home/opc/kawaki-outreach")

# One accent per slot so a grid of them never looks like the same image twice.
ACCENTS = ["#38bdf8", "#f59e0b", "#34d399", "#f472b6", "#a78bfa",
           "#fb7185", "#facc15", "#4ade80", "#22d3ee", "#c084fc"]

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;background:#0f172a;color:#e2e8f0;
  font-family:"Inter","Helvetica Neue",Arial,sans-serif;
  display:flex;flex-direction:column;justify-content:center;
  padding:96px;position:relative;overflow:hidden}
.rule{position:absolute;left:96px;top:96px;width:120px;height:8px;
  background:ACCENT;border-radius:4px}
.kicker{color:ACCENT;font-size:34px;letter-spacing:6px;font-weight:700;
  text-transform:uppercase;margin-bottom:48px}
h1{font-size:104px;line-height:1.06;font-weight:800;letter-spacing:-3px}
.sub{color:#94a3b8;font-size:40px;line-height:1.5;margin-top:56px;
  font-weight:400;max-width:860px}
.foot{position:absolute;left:96px;bottom:88px;right:96px;
  display:flex;justify-content:space-between;align-items:center;
  color:#64748b;font-size:30px;letter-spacing:2px}
.dot{color:ACCENT}
"""


def wrap_up_to(text, limit, sentence=False):
    """Keep whole words so a headline never cuts mid-word.

    sentence=True prefers ending on a full sentence: a subtitle that stops after
    "...the tools are not the" reads as a bug, not as a design choice.
    """
    words, out, n = text.split(), [], 0
    for w in words:
        if n + len(w) + 1 > limit and out:
            break
        out.append(w)
        n += len(w) + 1
    if not out:
        return text[:limit]
    cut = " ".join(out)
    if sentence and len(cut) < len(text):
        # back up to the last sentence end inside the cut, if there is one
        for sep in (". ", "! ", "? ", "\n"):
            i = cut.rfind(sep)
            if i > limit // 3:
                return cut[:i + 1].strip()
        # otherwise end on a whole word (already true) but mark it trimmed
        cut = cut.rsplit(" ", 1)[0] + "..."
    return cut


def render(hook, sub, out, accent, handle="kunalsharmaai"):
    css = CSS.replace("ACCENT", accent)
    page = f"""<!doctype html><meta charset=utf-8><style>{css}</style>
<div class=rule></div>
<div class=kicker>Kawaki Studios</div>
<h1>{html.escape(wrap_up_to(hook, 120))}</h1>
<div class=sub>{html.escape(wrap_up_to(sub, 180, sentence=True))}</div>
<div class=foot><span>linkedin.com/in/{handle}</span>
<span class=dot>&#9679;</span></div>"""

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350},
                        device_scale_factor=1)
        pg.set_content(page)
        pg.wait_for_timeout(150)          # fonts settle
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(out))
        b.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--sub", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--accent", default="")
    ap.add_argument("--day")
    ap.add_argument("--slot")
    a = ap.parse_args()

    if a.slot:
        day = a.day
        if not day:
            day = sorted((ROOT / "queue").iterdir())[-1].name
        src = ROOT / "queue" / day / f"{a.slot}_linkedin.txt"
        lines = [l for l in src.read_text().splitlines() if l.strip()]
        hook = lines[0] if lines else "Ship less."
        # second non-empty line is a whole sentence; joining paragraphs 2-3
        # produced a cut that stopped mid-clause on the first render
        rest = lines[1] if len(lines) > 1 else ""
        idx = int(a.slot) - 1
        accent = a.accent or ACCENTS[idx % len(ACCENTS)]
        if not a.sub:
            a.sub = rest
        text = hook
    else:
        text = a.text or ""
        if not text:
            print("need --text or --slot", file=sys.stderr)
            return 1
        accent = a.accent or ACCENTS[0]

    render(text, a.sub, a.out, accent)
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
