#!/usr/bin/env python3
"""llamaindex_audit.py - Checks a LlamaIndex RAG setup. SkillSeal edition."""
import sys, os, json
def audit(cfg):
    issues = []
    if not cfg.get("reader"): issues.append("no data reader/loader")
    if not cfg.get("index"): issues.append("no index built")
    if not cfg.get("query_engine"): issues.append("no query engine")
    if not cfg.get("node_parser"): issues.append("no node parser")
    score = max(0, 100 - len(issues)*20)
    return {"issues": issues, "score": score}
if __name__ == "__main__":
    if len(sys.argv) < 2: print("REPORT\nUsage: llamaindex_audit.py <json>"); sys.exit(1)
    inp = sys.argv[1]
    cfg = json.loads(inp) if not os.path.isfile(inp) else json.load(open(inp))
    r = audit(cfg)
    print("REPORT")
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
