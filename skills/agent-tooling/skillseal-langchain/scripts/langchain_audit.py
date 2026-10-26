#!/usr/bin/env python3
"""langchain_audit.py - Audits a LangChain RAG pipeline config. SkillSeal edition."""
import sys, os, json
def audit(cfg):
    issues = []
    if not cfg.get("retriever"): issues.append("no retriever configured")
    if not cfg.get("embedding"): issues.append("no embedding model set")
    if not cfg.get("vectorstore"): issues.append("no vector store")
    if not cfg.get("chunk_size"): issues.append("chunk_size not set")
    if not cfg.get("llm"): issues.append("no LLM configured")
    score = max(0, 100 - len(issues)*20)
    return {"issues": issues, "score": score}
if __name__ == "__main__":
    if len(sys.argv) < 2: print("REPORT\nUsage: langchain_audit.py <json>"); sys.exit(1)
    inp = sys.argv[1]
    cfg = json.loads(inp) if not os.path.isfile(inp) else json.load(open(inp))
    r = audit(cfg)
    print("REPORT")
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
