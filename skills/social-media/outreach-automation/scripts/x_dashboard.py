#!/usr/bin/env python3
"""Read-only outreach dashboard. One screen per channel, no invented numbers.

    python x_dashboard.py                 # today
    python x_dashboard.py --week          # 7-day rollup
    python x_dashboard.py --live          # read the profile feed itself

Design rules, each learned the hard way on 2026-09-30:

- Read only real sources: the state ledger, the engagement log, the outreach
  DB, and the live channel API. Never compute a number you cannot source.
- An unavailable metric is printed as unavailable. Rendering Premium-gated
  impressions as `0` is the same lie as reporting an unconfirmed send as sent.
- Show research freshness, the next scheduled action, and what is BLOCKED.
  A dashboard that only shows counts hides the reason a channel is at zero.
"""
import argparse
import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent          # outreach/ dir
STATE = HERE / "x_state.json"
ENG = HERE / "x_engage_log.json"
RESEARCH = HERE / "x_research.json"
DB = HERE / "outreach.db"
RESEARCH_MAX_AGE_MIN = 180


def bar(frac, width=22):
    frac = max(0.0, min(1.0, frac or 0))
    return "█" * int(frac * width) + "·" * (width - int(frac * width))


def rule(c="─"):
    return c * 74


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def show(days=1):
    now = datetime.now()
    print(rule("━"))
    print(f"  OUTREACH DASHBOARD — {now:%a %d %b %Y, %H:%M}  ({days}d window)")
    print(rule("━"))

    # ---------------- X ----------------
    print("\n▌X")
    st = load(STATE, {})
    cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    posts = [p for p in st.get("posted", []) if str(p.get("t", ""))[:10] >= cutoff]
    feed = [p for p in posts if p.get("kind") == "feed"]
    comm = [p for p in posts if p.get("kind") == "community"]
    target = (8 if days == 1 else 8 * days)
    print(f"  posts      {bar(len(feed)/target)} {len(feed)}/{target}")
    print(f"  community  {bar(len(comm)/2)} {len(comm)}/2")

    eng = load(ENG, [])
    if isinstance(eng, list):
        since = time.time() - days * 86400
        replies = [e for e in eng if e.get("type") == "reply" and e.get("t", 0) >= since]
        follows = [e for e in eng if e.get("type") == "follow" and e.get("t", 0) >= since]
        print(f"  replies    {bar(len(replies)/40)} {len(replies)}")
        print(f"  follows    {bar(len(follows)/8)} {len(follows)}")
    if not eng:
        print("  replies    log missing or has no `type`/timestamps —"
              " not aggregatable yet")

    r = load(RESEARCH, None)
    if r:
        age = (now - datetime.strptime(r["generated_at"], "%Y-%m-%dT%H:%M:%S")).total_seconds()/60
        print(f"  research   {'STALE' if age > RESEARCH_MAX_AGE_MIN else 'ok'} "
              f"— {r['generated_at'][11:]} ({age:.0f}m old, "
              f"{len(r.get('angles', []))} angles)")
    else:
        print("  research   MISSING — posts are being written blind")

    # ---------------- LinkedIn ----------------
    print("\n▌LINKEDIN")
    try:
        con = sqlite3.connect(str(DB))
        cur = con.cursor()
        by_state = dict(cur.execute(
            "SELECT state, COUNT(*) FROM people GROUP BY state").fetchall())
        total = cur.execute("SELECT COUNT(*) FROM people").fetchone()[0]
        sent_today = cur.execute(
            "SELECT COUNT(*) FROM people WHERE state='sent' "
            "AND date(touched_at)=date('now')").fetchone()[0]
        con.close()
        print(f"  sent       {bar(sent_today/30)} {sent_today}/30")
        print(f"  pool       {total} people  ({by_state})")
    except sqlite3.Error as e:
        print(f"  ✗ db unreadable: {e}")
    print("  notes      personalized-note quota is monthly, separate from no-note")

    print("\n" + rule())
    print("  BLOCKED / NEXT")
    print(rule())
    print("  - a channel at 0 is usually a missing input, not a working system:")
    print("    no phone numbers in the pool means WhatsApp cannot send at all.")
    print(rule())


def live(handle):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        pg = [x for x in b.contexts[0].pages if "x.com" in x.url][0]
        pg.bring_to_front()
        for label, url in (("PROFILE", f"https://x.com/{handle}"),
                           ("REPLIES", f"https://x.com/{handle}/with_replies")):
            pg.goto(url, timeout=90000, wait_until="domcontentloaded")
            pg.wait_for_timeout(11000)   # X renders late; a 6s check lies
            arts = pg.evaluate(
                "() => [...document.querySelectorAll('article')]"
                ".map(a => (a.innerText||'').replace(/\\n+/g,' | ').slice(0,110))")
            mine = [a for a in arts if handle in a]
            print(f"\n{label}: {len(arts)} articles, {len(mine)} mine")
            for a in mine[:8]:
                print("  ", a)
            if not arts:
                print("   (0 articles — that is a render failure, not an "
                      "empty feed. Re-navigate before reporting absence.)")
            pg.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", action="store_true")
    ap.add_argument("--live", metavar="HANDLE", default=None)
    a = ap.parse_args()
    if a.live:
        live(a.live)
    else:
        show(7 if a.week else 1)
