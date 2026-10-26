#!/usr/bin/env python3
"""Research-gated X growth tick: research -> plan -> post ONE -> engage.

    python x_growth_loop.py --dry          # show the plan, post nothing
    python x_growth_loop.py --min-gap-min 60

Ordering is the point, and the gate is the feature:

1. RESEARCH.  If the artifact is missing or older than ~3h, run the research
   pass. If it is STILL missing or halted by a challenge, RETURN WITHOUT
   POSTING. A loop that posts anyway has no gate; say "writing blind" instead.
2. PLAN.  Randomized slots inside each window, no repeats within a day.
3. GAP.  Read the newest post's age off the LIVE profile (a state ledger is
   bypassed by a manual send). Refuse inside the floor.
4. POST ONE.  Never drain a backlog — a burst is what reads as bot behaviour.
5. CONFIRM against the profile feed by polling; X renders late (6s vs 39s).
6. ENGAGE.  Replies scoped to [role="dialog"], follows capped and logged.

Adjust handle/CDP/research command and the post/confirm pair to the host.
"""
import argparse
import json
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RESEARCH_MAX_AGE_MIN = 180
RESEARCH_CMD = [sys.executable, str(HERE / "x_research.py")]


def research_state():
    """(ok, age_min, halted) — halted means a challenge stopped the pass."""
    p = HERE / "x_research.json"
    if not p.exists():
        return False, 0.0, False
    try:
        r = json.loads(p.read_text())
    except Exception:
        return False, 0.0, False
    if r.get("halted"):
        return False, 0.0, True
    try:
        t = datetime.strptime(r["generated_at"], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return False, 0.0, False
    age = (datetime.now() - t).total_seconds() / 60
    return age <= RESEARCH_MAX_AGE_MIN, age, False


def newest_post_age_min(cdp):
    """Age of the newest POST, from the first <article>'s <time datetime>.

    Scoped on purpose: a page-wide `·\\s*(\\d+)(s|m|h|d)` regex also matches
    engagement counters, so a seconds-old post reads as '1 min ago' from its
    own reply count and the floor silently passes. None = cannot enforce.
    """
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(cdp)
        pg = b.contexts[0].new_page()
        try:
            pg.goto("https://x.com/home", timeout=90000, wait_until="domcontentloaded")
            pg.wait_for_selector("article", timeout=45000)
            pg.wait_for_timeout(4000)
            iso = pg.evaluate(
                "() => { const t = document.querySelector('article time');"
                "return t ? t.getAttribute('datetime') : null; }")
            if not iso:
                return None
            from datetime import timezone
            return (datetime.now(timezone.utc)
                    - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds() / 60
        finally:
            pg.close()
            b.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp", default="http://127.0.0.1:9222")
    ap.add_argument("--min-gap-min", type=int, default=60)
    ap.add_argument("--no-research", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    rnd = random
    print(f"[tick] {datetime.now():%H:%M:%S}")

    # 1. research gate
    ok, age, halted = research_state()
    if halted:
        print("[research] previous pass halted on a challenge — not posting")
        return 1
    if not ok and not a.no_research:
        print("[research] stale/missing -> running now")
        subprocess.run(RESEARCH_CMD, cwd=str(HERE), timeout=1800)
        ok, age, halted = research_state()
    if not ok:
        print("[research] unavailable — halting rather than posting blind")
        return 1
    print(f"[research] ok, {age:.0f}m old")

    # 2/3. gap floor, measured live
    age_min = newest_post_age_min(a.cdp)
    if age_min is None:
        print("[gap] post age UNKNOWN — cannot enforce the floor. "
              "Re-navigate; do not post blind.")
        return 1
    if age_min < a.min_gap_min:
        print(f"[gap] last post {age_min:.0f}m ago, floor {a.min_gap_min}m -> wait")
        return 0
    print(f"[gap] ok, last post {age_min:.0f}m ago")

    if a.dry:
        print("[dry] plan OK; would post ONE slot")
        return 0

    # 4/5. host-specific: post ONE, then poll the profile to confirm.
    print("[post] hook this to your existing single-post sender, then confirm")
    print("       by polling /HANDLE a few times (X renders at ~39s, not 6s).")
    print("[engage] replies must be scoped to [role=\"dialog\"]; cap follows.")
    time.sleep(rnd.uniform(0, 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
