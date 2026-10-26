---
name: grounded-post-writer
description: Use when writing an X or LinkedIn post for Kawaki.
---

# Grounded Post Writer

Replaces a static pool file with a post derived from real research. The pool is
the *shape* of a good post, not the post.

## Why this exists

Measured 2026-10-02 on the 23-file `x_pool/`:

- 4 confession, 5 callout, 5 contrarian, 5 observation, 4 soft.
- Average 153 chars. **Zero concrete numbers, zero named tools, zero named
  people** across all 23.
- They read as category commentary: "most AI tools just create more decisions."

That is the same failure the comments had, in a different place. A post with no
specific is indistinguishable from the other 40 posts saying it.

## The rule

**A post must contain, or be built around, at least one thing only you know.**

- a number you actually measured, or
- a named tool with a named result, or
- a named person or client situation (anonymised if needed), or
- a specific failure you caused and what it cost.

No number → no post. If you do not have one today, do not post. Say so.

## Procedure

1. **Load research.** Read `x_research.json`. It holds scored angles with
   permalinks. Take the top-scoring angle for the lane. If `angles[]` is empty
   or `halted: true`, **stop** — do not write blind.
2. **Pick the shape from the pool, not the words.** `x_pool/NN_kind.txt` gives
   you the structure: confession opens with absence, callout asks a real
   question, contrarian takes a side, observation is a reframe, soft is a light
   admission.
3. **Write the body yourself.** The pool file is a reference for structure
   only. Copying its text is the bug this skill fixes.
4. **Ground it.** Insert the specific from research: the handle, the URL, the
   number, the tool. Cite the source link in the post or the first reply.
5. **Record the grounding.** Every post carries `angle_url`, `angle_score`, and
   `grounded_detail` in `x_state.json`. A post with `grounded_detail: ""` is a
   regression and should fail the review.

## Self-check before posting

- [ ] At least one number, named tool, or named situation
- [ ] Under 280 chars (X) or the agreed LinkedIn length
- [ ] No banned opener ("In today's fast-paced world", "game-changer",
      "leverage", "fundamentally", "deep dive")
- [ ] No em dashes
- [ ] 0-2 hashtags, at the end
- [ ] Links moved to first reply, not the body
- [ ] Does not read like the other 40 posts in the lane

## Banned failure modes

- **Category commentary.** "AI is changing how we work" says nothing.
- **Rule of three with no receipts.** Three items, none specific.
- **Borrowed specificity.** Using someone else's number as if it were yours.
  Cite it or drop it.
- **Posting because the schedule said so.** An empty research file is a
  legitimate reason to post zero. That is not a failure, it is the gate.

## Related

- `no-comments-guard` — comments are off entirely, posting only
- `seo-vault-voice` — the voice-and-proof discipline, same principle
- `evidence-before-claiming` — never claim a post went out without the permalink
