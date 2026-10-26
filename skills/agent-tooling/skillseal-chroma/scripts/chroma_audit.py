#!/usr/bin/env python3
"""chroma_audit.py - Checks a Chroma vector store config. SkillSeal edition."""
import sys, os, json
def audit(cfg):
    issues = []
    if not cfg.get("collection"): issues.append("no collection specified")
    if not cfg.get("embedding_function"): issues.append("no embedding function")
    if not cfg.get("distance"): issues.append("no distance metric (e.g. l2/cosine)")
    if not cfg.get("persist"): issues.append("no persistence configured")
    score = max(0, 100 - len(issues)*20)
    return {"issues": issues, "score": score}
if __name__ == "__main__":
    if len(sys.argv) < 2: print("REPORT\nUsage: chroma_audit.py <json>"); sys.exit(1)
    inp = sys.argv[1]
    cfg = json.loads(inp) if not os.path.isfile(inp) else json.load(open(inp))
    r = audit(cfg)
    print("REPORT")
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
