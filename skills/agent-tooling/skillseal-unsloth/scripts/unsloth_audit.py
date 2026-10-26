#!/usr/bin/env python3
"""unsloth_audit.py - Audits unsloth configuration. SkillSeal edition."""
import sys, os, json
def audit(cfg):
    issues = []
    if isinstance(cfg, dict):
        if not cfg.get("model"): issues.append("model not set")
    if not cfg.get("max_seq_length"): issues.append("max_seq_length not set")
    if not cfg.get("load_in_4bit"): issues.append("load_in_4bit not set")
    score = max(0, 100 - len(issues)*20)
    return {"issues": issues, "score": score}
def load(inp):
    if os.path.isfile(inp):
        with open(inp) as f: return json.load(f)
    try: return json.loads(inp)
    except: return {}
if __name__ == "__main__":
    if len(sys.argv) < 2: print("REPORT\nUsage: unsloth_audit.py <json_or_file>"); sys.exit(1)
    r = audit(load(sys.argv[1]))
    print("REPORT")
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
