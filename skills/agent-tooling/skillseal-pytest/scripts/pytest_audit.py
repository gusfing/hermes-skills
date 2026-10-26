#!/usr/bin/env python3
"""pytest_audit.py - Audits pytest test structure and quality. SkillSeal edition."""
import sys, os, re, json
def audit(data):
    issues = []
    if isinstance(data, dict):
        files = data.get("test_files", [])
    else:
        files = str(data).split(",")
    for f in files:
        if not f.strip(): continue
        name = f.strip().lower()
        if not name.startswith("test_"):
            issues.append(f"{f}: should start with test_")
        if "fixture" not in name and "mock" not in name:
            pass
    total = len([f for f in files if f.strip()])
    score = max(0, 100 - len(issues)*10)
    return {"test_files": total, "issues": issues, "score": score}
def load(inp):
    if os.path.isfile(inp):
        with open(inp) as f: return json.load(f)
    try: return json.loads(inp)
    except: return {"test_files": inp.split(",")}
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("REPORT\nUsage: pytest_audit.py <json_or_file>"); sys.exit(1)
    r = audit(load(sys.argv[1]))
    print("REPORT")
    print("Test files:", r["test_files"])
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
