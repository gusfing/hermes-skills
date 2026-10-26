# Template-bank spray: the arithmetic of visible repetition

Session: 2026-10-02, @Kunalsharmadec6 + LinkedIn. The user read his own feed
and said the comments were stupid, then set the scope: posting only.

## What was actually wrong

Not wording. Arithmetic.

```python
REPLY_FRAMES = [6 shapes]
POINTS        = [8 fixed strings]
body = rnd.choice(REPLY_FRAMES).format(point=rnd.choice(POINTS))
if topic not in body:
    body = f"{body} — especially around {topic.lower()}."
```

6 x 8 = **48 reachable outputs**, lifetime. Then `topic` was
`re.findall(r"\b[A-Z][a-z]{4,}\b", text)[0]` — the first capitalised word
scraped from the target post. When that word was a name, live replies read:

> "this matches what we hit — half the cost is maintenance, not setup —
>  especially around shakhzod."

## Measurements (from `x_engage_log.json`)

| Metric | Value |
|---|---|
| replies logged | 101 (89 timestamped) |
| per day | 09-30: 21, 10-01: 42, 10-02: 26 |
| distinct opening clauses | 31 |
| `this matches what we hit` | 15 |
| `we built around this` | 15 |
| distinct handles replied to | 76 |

76 handles means this was not one bad thread. It was machine spray across a
whole network, which is exactly what the owner noticed.

## LinkedIn was worse

```python
r = do_comment(s, i, random.choice(COMMENTS))   # 6 strings, post never read
log({"type": "comment", "post": txt[:90], "url": url})   # no text field at all
```

- 35 comments on 20 distinct posts
- the target post's content was **never** read
- the emitted text was **never stored**, so the damage could not be audited

That last point is the one to generalise: **store the exact payload you emit.**
When the user objects, the log is the only way to scope the damage and the only
way to prove the fix.

## The audit that detects this class of bug

Mask the variable slot, count the remaining shapes:

```python
from collections import Counter
import re

def shapes(rows, slot_re=r"\s—\s especially around .*$"):
    return Counter(re.sub(slot_re, "", r["text"]).strip().lower() for r in rows)

c = shapes([r for r in replies if r["type"] == "reply"])
print(len(c), "distinct shapes from", len(replies), "rows")
for t, n in c.most_common(5):
    print(f"{n:>4}x {t[:80]}")
```

**Run this before adding any canned bank, and again after.** A bank whose
distinct-shape count is a small fraction of its row count is rotation, not
variety.

## Removal, without breaking posting

Deleting the emission path is easy; deleting it *cleanly* is where dead code
appears. Two things to watch:

1. A `continue` inserted above a block leaves the block unreachable but
   present — the follow-on logic silently stops running too. Delete the block,
   do not shadow it.
2. Removing `do_comment()` orphans its helpers. `do_comment` called `_submit`
   (which verified via the `createComment` network response) and `_type_keys`.
   Both became dead and had to go, or the checker's own patterns kept matching
   them.

After removal, re-parse with `ast.parse` and re-run the checker. `ast.parse`
catches truncation from a scripted deletion; the checker catches what survives.

## The checker

`scripts/forbidden_path_check.py`. Docstrings are stripped before matching, so
the measurement notes kept inside the code (including the ones about the bug
being fixed) do not trip it. Verified by injection:

```
# with a fake do_comment() injected
FAIL  1 comment path(s) present:
  li_engage.py:107  LinkedIn comment dispatch
exit=1 (want 1)
# restored
PASS  no forbidden code paths
exit=0 (want 0)
```

## Related trap: the same disease in the posting path

The post pool had the identical failure in a different place. All 23 files,
average 153 chars, **zero numbers, zero named tools, zero named people**:

> "The more AI tools I try, the more I realize most of them just create more
>  decisions. The ones that stick are the ones that remove decisions."

Unmistakable from the rest of the lane. Fix: a post must carry something only
the author knows, and pool files supply *shape* only.
