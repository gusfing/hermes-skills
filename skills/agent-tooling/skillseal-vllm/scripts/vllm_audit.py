#!/usr/bin/env python3
"""vllm_audit.py - Checks a vLLM serving config. SkillSeal edition."""
import sys, os, json
def audit(cfg):
    issues = []
    if not cfg.get("model"): issues.append("no model path/hf-id")
    if not cfg.get("tensor_parallel"): issues.append("tensor_parallel not set")
    if not cfg.get("max_model_len"): issues.append("max_model_len not set")
    if not cfg.get("gpu_memory"): issues.append("gpu_memory_utilization not set")
    score = max(0, 100 - len(issues)*20)
    return {"issues": issues, "score": score}
if __name__ == "__main__":
    if len(sys.argv) < 2: print("REPORT\nUsage: vllm_audit.py <json>"); sys.exit(1)
    inp = sys.argv[1]
    cfg = json.loads(inp) if not os.path.isfile(inp) else json.load(open(inp))
    r = audit(cfg)
    print("REPORT")
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
