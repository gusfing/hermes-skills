#!/usr/bin/env python3
"""whisper_audit.py - Checks Whisper transcription setup. SkillSeal edition."""
import sys, os, json
def audit(cfg):
    issues = []
    if not cfg.get("model"): issues.append("no model size (tiny/base/small/medium/large)")
    if not cfg.get("language"): issues.append("no language specified")
    if not cfg.get("output_format"): issues.append("no output format (txt/srt/json)")
    if not cfg.get("device"): issues.append("no device (cpu/cuda)")
    score = max(0, 100 - len(issues)*20)
    return {"issues": issues, "score": score}
if __name__ == "__main__":
    if len(sys.argv) < 2: print("REPORT\nUsage: whisper_audit.py <json>"); sys.exit(1)
    inp = sys.argv[1]
    cfg = json.loads(inp) if not os.path.isfile(inp) else json.load(open(inp))
    r = audit(cfg)
    print("REPORT")
    print("Score:", r["score"])
    for i in r["issues"]: print(" -", i)
    sys.exit(0 if r["score"] >= 60 else 1)
