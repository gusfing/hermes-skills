#!/usr/bin/env python3
"""peft_audit.py - Audits peft configuration. SkillSeal edition."""
import sys, os, json
def audit(cfg):
    issues = []
    if isinstance(cfg, dict):
        if not cfg.get("base_model"): issues.append("base_model not set")
    if not cfg.get("method"): issues.append("method not set")
    if not cfg.get("lora_rank"): issues.append("lora_rank not set")
    score = max(0, 100 - len(issues)*20)
    return {"issues": issues, "score": score}
def load(inp):
    if os.path.isfile(inp):
        with open(inp) as f: return json.load(f)
    try: return json.loads(inp)
    except: return {}
if __name__ == "__main__":
    if len(sys.argv) < 2: print("REPORT\nUsage: peft_audit.py <json_or_file>"); sys.exit(1)
    r = audit(load(sys.argv[1]))
    print("REPORT")
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
