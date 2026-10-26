#!/usr/bin/env python3
"""drf_audit.py - Checks Django REST Framework setup. SkillSeal edition."""
import sys, os, json
def audit(cfg):
    issues = []
    if not cfg.get("serializers"): issues.append("no serializers defined")
    if not cfg.get("views"): issues.append("no viewsets defined")
    if not cfg.get("urls"): issues.append("no router urls")
    if not cfg.get("permissions"): issues.append("no permission classes")
    score = max(0, 100 - len(issues)*20)
    return {"issues": issues, "score": score}
if __name__ == "__main__":
    if len(sys.argv) < 2: print("REPORT\nUsage: drf_audit.py <json>"); sys.exit(1)
    inp = sys.argv[1]
    cfg = json.loads(inp) if not os.path.isfile(inp) else json.load(open(inp))
    r = audit(cfg)
    print("REPORT")
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
