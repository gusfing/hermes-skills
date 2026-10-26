#!/usr/bin/env python3
"""ts_audit.py - Checks TypeScript config quality. SkillSeal edition."""
import sys, os, json
def audit(cfg):
    issues = []
    strict = cfg.get("strict")
    if strict is not True: issues.append("strict mode not enabled")
    if not cfg.get("noImplicitAny"): issues.append("noImplicitAny not set")
    if not cfg.get("target"): issues.append("target not specified")
    score = max(0, 100 - len(issues)*25)
    return {"issues": issues, "score": score}
if __name__ == "__main__":
    if len(sys.argv) < 2: print("REPORT\nUsage: ts_audit.py <json>"); sys.exit(1)
    inp = sys.argv[1]
    cfg = json.loads(inp) if not os.path.isfile(inp) else json.load(open(inp))
    r = audit(cfg)
    print("REPORT")
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
