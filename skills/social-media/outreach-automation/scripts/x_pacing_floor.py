#!/usr/bin/env python3
"""Measure the real post pace on an X profile, from the live DOM.

Use before any multi-post run and before reporting engagement. Both jobs were
done wrong by hand on 2026-09-30: a whole-page timestamp regex matched
engagement counters instead of a post time, and an analytics parse reported
Premium-gated metrics as None/zero.

Run with the venv python that has playwright installed, against an already
logged-in Chrome exposed on CDP (see remote-desktop / browser-backends).

    python x_pacing_floor.py --handle Kunalsharmadec6 --cdp http://127.0.0.1:9222
    python x_pacing_floor.py --handle Kunalsharmadec6 --engage

--engage additionally reports per-post engagement. It deliberately reports
"unmeasurable" instead of 0 when the counters are not rendered, because X
gates impressions/reach behind Premium.
"""
import argparse
import re
import sys
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

AGE_RE = re.compile(r"·\s*(\d+)\s*(s|m|h|d)", re.I)
COUNTER_RE = re.compile(r"^\s*[\d.,]+[KMB]?\s*$")


def age_minutes(text):
    """Parse X's relative stamp ('· 5m', '· 2h') into minutes, or None."""
    if not text:
        return None
    m = AGE_RE.search(text)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2).lower()
    return {"s": n / 60.0, "m": n, "h": n * 60, "d": n * 1440}[unit]


def first_article_stamp(pg):
    """Age of the NEWEST post only.

    Scope to the first <article> on purpose. A page-wide regex also matches
    engagement counters, so a brand new post reads as '1 min ago' from its
    reply count and a rate-limit floor silently passes.
    """
    return pg.evaluate(
        """() => {
            const a = document.querySelector('article');
            if (!a) return null;
            const t = a.querySelector('time');
            if (!t) return null;
            return {iso: t.getAttribute('datetime'), text: t.innerText};
        }"""
    )


def iter_posts(pg, limit):
    out = []
    for el in pg.query_selector_all("article")[:limit]:
        d = el.evaluate(
            """n => {
                const t   = n.querySelector('time');
                const body = n.innerText || '';
                const nums = (body.match(/[\\d.,]+[KMB]?/g) || []).map(s => s.trim());
                const stats = (n.querySelector('[data-testid="reply"]') || {}) ?
                    null : null;
                return {
                    when: t ? (t.getAttribute('datetime') || t.innerText) : null,
                    url : t ? t.closest('a')?.getAttribute('href') || null : null,
                    text: body.slice(0, 120)
                };
            }"""
        )
        out.append(d)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", required=True)
    ap.add_argument("--cdp", default="http://127.0.0.1:9222")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--floor", type=int, default=90,
                    help="refuse if the newest post is younger than this (minutes)")
    ap.add_argument("--engage", action="store_true",
                    help="also print a per-post engagement table")
    a = ap.parse_args()

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(a.cdp)
        pg = b.contexts[0].new_page()
        pg.goto(f"https://x.com/{a.handle}", wait_until="domcontentloaded")
        pg.wait_for_selector("article", timeout=45000)
        pg.wait_for_timeout(4000)   # feed hydrates late; one check = false negative

        stamp = first_article_stamp(pg)
        if stamp and stamp.get("iso"):
            age = (datetime.now(timezone.utc)
                   - datetime.fromisoformat(stamp["iso"].replace("Z", "+00:00")))
            mins = age.total_seconds() / 60.0
            print(f"newest post: {mins:.1f} min old  ({stamp['text']})")
            if mins < a.floor:
                print(f"REFUSING: floor is {a.floor} min. "
                      f"Wait {a.floor - mins:.0f} min or post into the next slot.")
                print("Posting in a burst is what gets an account limited.")
                sys.exit(2)
            print(f"floor OK ({a.floor} min)")
        else:
            print("newest post: age UNKNOWN -> floor cannot be enforced. "
                  "Do not batch-post blind; re-navigate and retry.")
            sys.exit(3)

        if a.engage:
            print(f"\nlast {a.limit} posts (newest first):")
            for i, d in enumerate(iter_posts(pg, a.limit), 1):
                print(f"{i:2}. {d.get('when')}  {d.get('url')}")
                print(f"    {d.get('text', '')[:100]!r}")
            print("\nNote: impressions and reach are Premium-gated on X. If the "
                  "per-post counters did not render, that is 'unmeasurable', "
                  "NOT 'zero engagement'.")

        pg.close()
        b.close()


if __name__ == "__main__":
    main()
