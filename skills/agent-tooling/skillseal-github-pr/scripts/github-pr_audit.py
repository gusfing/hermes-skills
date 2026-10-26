#!/usr/bin/env python3
"""pr_audit.py - Reviews GitHub PR quality checklist. SkillSeal edition."""
import sys, os, json
def audit(pr):
    issues = []
    title = pr.get("title", "")
    body = pr.get("body", "")
    if len(title) < 10: issues.append("title too short")
    if len(body) < 30: issues.append("description too short")
    if not pr.get("tests"): issues.append("no tests mentioned")
    if not pr.get("changelog"): issues.append("no changelog entry")
    score = max(0, 100 - len(issues)*20)
    return {"issues": issues, "score": score}
if __name__ == "__main__":
    if len(sys.argv) < 2: print("REPORT\nUsage: pr_audit.py <json>"); sys.exit(1)
    inp = sys.argv[1]
    pr = json.loads(inp) if not os.path.isfile(inp) else json.load(open(inp))
    r = audit(pr)
    print("REPORT")
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
