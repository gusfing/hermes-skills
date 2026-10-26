#!/usr/bin/env python3
"""react_audit.py - Checks React 19 app best practices. SkillSeal edition."""
import sys, os, json
def audit(cfg):
    issues = []
    if cfg.get("keys_missing"): issues.append("missing keys in lists")
    if cfg.get("state_lifting_needed"): issues.append("state should be lifted")
    if cfg.get("memoization_missing"): issues.append("missing useMemo/useCallback")
    if not cfg.get("error_boundary"): issues.append("no error boundary")
    score = max(0, 100 - len(issues)*20)
    return {"issues": issues, "score": score}
if __name__ == "__main__":
    if len(sys.argv) < 2: print("REPORT\nUsage: react_audit.py <json>"); sys.exit(1)
    inp = sys.argv[1]
    cfg = json.loads(inp) if not os.path.isfile(inp) else json.load(open(inp))
    r = audit(cfg)
    print("REPORT")
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
