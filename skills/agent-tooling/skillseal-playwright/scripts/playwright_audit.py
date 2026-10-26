#!/usr/bin/env python3
"""playwright_audit.py - Checks Playwright test config and selectors. SkillSeal edition."""
import sys, os, json
def audit(cfg):
    issues = []
    if isinstance(cfg, dict):
        base = cfg.get("base_url", "")
        headless = cfg.get("headless", None)
        if not base: issues.append("base_url not set")
        if headless is None: issues.append("headless not configured")
        for sel in cfg.get("selectors", []):
            if len(sel) < 2: issues.append(f"weak selector: {sel}")
    score = max(0, 100 - len(issues)*15)
    return {"issues": issues, "score": score}
if __name__ == "__main__":
    if len(sys.argv) < 2: print("REPORT\nUsage: playwright_audit.py <json>"); sys.exit(1)
    inp = sys.argv[1]
    cfg = json.loads(inp) if not os.path.isfile(inp) else json.load(open(inp))
    r = audit(cfg)
    print("REPORT")
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
