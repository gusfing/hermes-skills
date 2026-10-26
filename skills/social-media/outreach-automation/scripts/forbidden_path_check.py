#!/usr/bin/env python3
"""Fails if automation contains a code path the owner has forbidden.

Use for any standing "this must never come back" directive — commenting,
DM-ing a competitor, writing to prod, touching a user's everyday browser.

Run before restarting a timer. Exit 1 means the capability returned.

Two details that make it a real gate:
  * docstrings and comments are stripped before matching, so the checker
    cannot be defeated by its own documentation (or made unsatisfiable by it).
  * verify it fails: inject a fake violating function, confirm exit 1, restore.
    A checker that has only ever printed PASS is untested.
"""
import ast
import io
import os
import re
import sys
import tokenize
from pathlib import Path

# Where the audited automation lives. Override per host:
#   FORBIDDEN_PATH_CHECK_ROOT=/path/to/repo python3 forbidden_path_check.py
ROOT = Path(
    os.environ.get("FORBIDDEN_PATH_CHECK_ROOT")
    or Path(__file__).resolve().parent.parent.parent.parent.parent / "kwaki-outreach"
)

# (filename, regex, why). Match GENERATION or EMISSION, not the word in a log key.
FORBIDDEN = [
    # Posting-only directive (user, 2026-10-02). Posting is allowed; commenting is not.
    ("x_engage.py", r"\btweetButton\b", "X reply composer"),
    ("x_engage.py", r"REPLY_FRAMES", "X canned reply bank"),
    ("x_engage.py", r"keyboard\.type\(body", "X reply typing"),
    ("li_engage.py", r"\bCOMMENTS\s*=\s*\[", "LinkedIn canned comment bank"),
    ("li_engage.py", r"createComment", "LinkedIn comment API call"),
    ("li_engage.py", r"do_comment\(", "LinkedIn comment dispatch"),
    # A scraped token spliced into a template — see the canned-bank section.
    ("x_engage.py", r"especially around|specifically around", "X topic splice"),
]


def code_lines(path: Path) -> list[tuple[int, str]]:
    """Source with comments and docstrings removed.

    A docstring documenting a past measurement is evidence, not a code path.
    Counting it would make the check impossible to satisfy without deleting
    hard-won notes.
    """
    src = path.read_text(errors="replace")
    drop = {t.start[0] for t in tokenize.generate_tokens(io.StringIO(src).readline)
            if t.type == tokenize.COMMENT}
    try:
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef, ast.Module)):
                if ast.get_docstring(node, clean=False) is not None:
                    first = node.body[0]
                    drop.update(range(first.lineno, first.end_lineno + 1))
    except SyntaxError:
        pass
    return [(n, l) for n, l in enumerate(src.splitlines(), 1) if n not in drop]


def main() -> int:
    bad = []
    missing = []
    for fname, pat, why in FORBIDDEN:
        p = ROOT / fname
        if not p.exists():
            # Do NOT skip silently. A missing target means this check is
            # inspecting nothing and would report PASS forever -- the rubber
            # stamp this script exists to prevent.
            missing.append(fname)
            continue
        for n, line in code_lines(p):
            if re.search(pat, line):
                bad.append(f"  {fname}:{n}  {why}\n      {line.strip()[:88]}")

    if missing:
        print("FAIL  audit target(s) not found -- checks did not run:\n")
        for fname in missing:
            print(f"  {fname}  (looked in {ROOT})")
        print("\nFix ROOT or move the file. An unaudited path is not a clean path.")
        return 1

    if not bad:
        print(f"PASS  no forbidden code paths  ({len(FORBIDDEN)} checks, {ROOT})")
        return 0
    print(f"FAIL  {len(bad)} forbidden path(s) present:\n")
    print("\n".join(bad))
    return 1


if __name__ == "__main__":
    sys.exit(main())
