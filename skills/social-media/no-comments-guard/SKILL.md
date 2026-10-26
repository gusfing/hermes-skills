---
name: no-comments-guard
description: Use when engagement automation would comment or reply.
---

# NO COMMENTS. NO REPLIES. POSTING ONLY.

**Owner directive, 2026-10-02.** Read this before touching any X or LinkedIn
automation. This overrides every older instruction that says comment, reply,
engage-in-thread, or drip replies.

## The rule

- **X:** post only. No replies, no quote tweets, no thread self-replies.
- **LinkedIn:** post only. No comments, no reactions to be posted later.
- **Comments are a hard block, not a lower probability.** Not `0.2`, not
  `random.random() > 0.2`. There is no code path that emits a comment.

## Why (measured, not guessed)

From `x_engage_log.json`, 101 replies over three days:

- 6 reply frames x 8 hardcoded "points" = **48 possible replies total**, then a
  random capitalised noun lifted from the post spliced onto the end:
  `"... — especially around {topic}."`
- 89 timestamped replies used **31 distinct opening clauses**; `this matches what
  we hit` and `we built around this` each appeared **15 times**.
- Replied to 76 distinct handles, so this was not one bad thread — it was
  machine spray across the whole network.
- `li_engage.py` was worse: 6 hardcoded comments via `random.choice()`, **text
  never read once**, 35 comments on 20 distinct posts, and the posted text was
  never saved to the log so it could not even be audited.

The owner read these in his own feed and called them stupid. The diagnosis is
the combinatorial repeat rate, not the wording.

## The enforcement

`x_engage.py` and `li_engage.py` must not contain a comment-emitting code path.
Verification:

```bash
cd /home/opc/kawaki-outreach
python3 x_selfcheck.py
```

`x_selfcheck.py` fails if a comment path exists. Run it before any restart of
the automation.

## If asked to re-enable comments later

Do not treat that as a toggle. Restoring comments means rewriting generation
so it reads the target post and derives substance from it, plus an approval
step. See `linkedin-comment-drafter` and `linkedin-reply-handler` for the
generator patterns that read the post first. Until that exists, comments stay
off.
