#!/usr/bin/env python3
"""faiss_audit.py - Checks a FAISS index setup. SkillSeal edition."""
import sys, os, json
def audit(cfg):
    issues = []
    if not cfg.get("index_type"): issues.append("no index type (flat/ivf/hnsw)")
    if not cfg.get("dimension"): issues.append("no vector dimension")
    if not cfg.get("metric"): issues.append("no metric (l2/inner_product)")
    if not cfg.get("normalize"): issues.append("consider normalize=True for cosine")
    score = max(0, 100 - len(issues)*20)
    return {"issues": issues, "score": score}
if __name__ == "__main__":
    if len(sys.argv) < 2: print("REPORT\nUsage: faiss_audit.py <json>"); sys.exit(1)
    inp = sys.argv[1]
    cfg = json.loads(inp) if not os.path.isfile(inp) else json.load(open(inp))
    r = audit(cfg)
    print("REPORT")
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
