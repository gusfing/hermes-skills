# Passing the machine-writing gate

Session 2026-10-09. Three LinkedIn drafts written from live X threads, scored
with the `li-human` detector (`detect.py`), all three had to reach PASS before
any card was rendered.

## What the score actually measures

`detect.py` runs five checks, each 0-100; the mean is HUMAN SCORE. 70+ is PASS,
but one weak check drags the mean under on its own.

| check | measures | human / machine anchors |
|---|---|---|
| BURSTINESS | stdev/mean of sentence lengths | 0.70 / 0.22 |
| SPECIFICITY | (digit tokens + distinct capitalised words) per 100 words | 6.0 / 0.5 |
| SLOP DENSITY | stock vocabulary from `slop.json` per 100 words | - |
| FINGERPRINT | invisible chars, em dashes, curly quotes, ellipsis chars, hard spaces | - |
| VOICE | contractions + personal pronouns per 100 words, structural tells | - |

Run it as `python3 detect.py <file>`, and `humanize.py <in> -o <out> --report`
first — humanize strips artefacts, detect judges. Score the **clean** file; the
raw draft and the clean file differ.

## SPECIFICITY is the check that fails, and it is a density

Measured: two of three drafts came back **45.2 and 46.2 FLAGGED**, both on
`2 concrete markers, 0.9 per 100 words (want 4+)`. The prose was fine. The
arithmetic was not: markers count in *absolute* terms, the score is *per 100
words*.

So there are two levers, and you need both:

1. **Add named/numeric markers drawn from the source material.**
2. **Cut words.** A 1,300-char draft holding 5 markers scores worse than a
   1,100-char draft holding the same 5.

## Anonymous attribution is the most expensive habit

`Someone below it replied`, `Another reply put it as`, `One reply:` — each costs
markers and buys nothing. The harvested thread JSON already holds the real
display name and the exact like count.

Converting *one* anonymous attribution to a real handle plus its number, while
cutting roughly 150 words, moved a draft **45.2 -> 85.5**.

- before: `Someone below it posted a working compiler...`
- after: `Underneath it, Jeryd posted a compiler and an inference engine in Rust...`
- plus an opening that leads with `4,179 likes, 766 replies and 510,247 views`

**Every quote in a post carries the speaker's name and the measured count. If
the name is not in the source file, the quote is not usable.** This is the same
rule as `grounded-post-writer`'s specificity gate, applied to quotes rather than
to claims.

## Read the check, do not guess at the number

Each check is about ten lines, with its thresholds as literals in
`scale(value, human=..., machine=...)`. When a score looks wrong, read the check
function — the numerator is usually what you assumed and the denominator is not.
Same discipline as the metric-parser work in
`reading-conversations-on-x.md`: measure the instrument before you edit prose to
chase its output.

## The card headline must read standalone

The card quote is lifted out of the post body, where the surrounding sentences
carry it. On the card it stands alone against a large typeface.

Measured failure: the body fragment
`The line isn't can AI build hard things. It's does the mistake announce itself.`
rendered as a headline and reads as broken English. Resent as
`Does the mistake announce itself? That's the whole line.`

`vision_analyze` caught it only because the question asked, and reported it as
"quote wording looks grammatically off (content issue, not layout)". Ask the
vision pass for **both**: layout (clipping, overlap, complete subtitle) AND
whether the headline is a complete grammatical statement. A layout-only question
returns "all clear" on a card that reads wrong.

## A 280-char score is not evidence about a 1,100-char post

Measured 2026-10-11 on two real queued slots: `li_a_vibeline` scored **85.5** on
its own file (1,150 ch), yet the slot wired into the calendar scored
**1064 chars / 16.9 FLAGGED**. Nothing was rewritten — the slot is a different
revision, and at 1,064 chars it sits under the measured band.

Two traps this exposes:

- **Score the exact revision that ships.** A PASS recorded against
  `drafts/x.txt` says nothing about the copy in `queue/.../01_linkedin.txt` or in
the studio slot. Re-run `detect.py` against the shipping text before claiming a
score.
- **A score and a length band are different gates, and passing one is not
  passing the other.** SPECIFICITY is per 100 words, so a shorter revision of the
  same draft can fail specificity and sit under the band at once. Check the
  character count against `1599-1855` independently of the humanizer score.

When they disagree, report both numbers rather than the better one.

## Presenting the set

Hand over all drafts in one message with: the hook formula used, character count,
the humanizer score, and what is still unpublished. **Attach no card** — the
owner supplies the image now (see the SKILL.md override, 2026-10-11): draft the
text, present it, stop, wait. Cards are rendered only when explicitly asked for.
Do not publish — the queue is the deliverable.
