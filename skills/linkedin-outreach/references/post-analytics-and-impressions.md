# LinkedIn post analytics: what renders where

Measured 2026-10-03 on a logged-in Chrome + CDP session.

## The feed renders ZERO engagement counts

Every reaction button on `/feed/` reads:

```
Reaction button state: no reaction
```

0 of 3 posts exposed any reaction, comment, or view number. Combined with the
absence of any permalink or `urn:li:activity` on a feed card (see SKILL.md), a
**LinkedIn feed cannot be ranked by performance from the feed itself.**

So: "what works on LinkedIn" cannot be answered by scraping the feed. Saying
otherwise would be fabricating a finding.

## The owner's own activity page DOES render them

```
https://www.linkedin.com/in/<handle>/recent-activity/all/
```

Measured live:

```
116 impressions  ·  3 reactions  ·  2 comments
 97 impressions
 48 impressions
 46 impressions
 48 impressions
```

Selectors:

| what | selector |
|---|---|
| impressions counter | `span.ca-entry-point__num-views` (10 nodes) |
| card | `div.feed-shared-update-v2__control-menu-container` (5 nodes) |
| author | `button[aria-label^="Open control menu for post by"]` |

**This page has zero `<p>` elements.** A "longest `<p>`" body extractor —
which is correct on the feed — returns nothing here. Use the card container's
`innerText` plus a noise-line filter (drop the counter lines, "…more", "Follow",
"Like", "Comment", `Nw/Nd/Nm` ages, bare reaction pills).

Two surfaces, two different DOM shapes. **A selector validated on one is
invalid on the other.** Do not port one extractor across both.

## Reading the handle from the page, never guessing

```
kunal-sharma-9aa97312  ->  404
kunalsharmaai          ->  renders
```

Get it from the live feed rather than guessing:

```javascript
document.querySelector('[componentkey*="_IDENTITY_PROFILE"] a[href*="/in/"]')
```

A plausible-looking vanity URL is a silent dead end that costs a full
navigation to discover.

Two more URL traps hit in the same pass:

- `href` values off identity links come back **already absolute**. Prepending
  the host yields `https://www.linkedin.comhttps://www.linkedin.com/in/...`.
- The route 404s without a trailing pattern — `/recent-activity/all/` renders,
  `/recent-activity/all` 404s.

## Feed structure, measured on 3 posts

| property | value |
|---|---|
| body length | 1132, 2416, 2991 chars (median 2416) |
| paragraphs | 26-32 |
| hashtags | 6, 1, 8 |
| body link | 1 of 3 |
| CTA | 0 of 3 |
| media | 3 of 3 (image or video, 1 video) |

**n=3 is a census, not a pattern.** "Every post carried media" describes what
the feed contained that morning; it is not evidence that media drives reach.
State the sample size or do not draw the inference.

## Carousel vs single image

Document posts win because **a swipe is counted and a scroll is not** —
1080x1350 PDF, 8-12 slides, cover slide is ~80% of the result, 6 words on it,
number every slide, recap slide is what gets screenshotted, handle small in
every corner.

The owner's posts carry images but are single-image, which is the weaker
version. The swipe is the measured thing.

## Consequence for writing

Own-side impressions are the only real performance data available. Compute
ratios from them the way they were computed for X (number-in-hook, CTA,
length bands) before asserting any "what works" claim on LinkedIn. Until then,
say the ratio is unmeasured rather than borrowing X's numbers across platforms.

## Own-post harvest: what actually came back (2026-10-04)

Ran the extraction against `/in/kunalsharmaai/recent-activity/all/` and got
**5 posts, not 3** — the feed census above and the own-post count are different
samples and must never be pooled.

```
imp=167 chars=1631 paras=11 rx=null cm=2
imp= 98 chars=1777 paras=11 rx=null cm=null
imp= 48 chars=1636 paras=13 rx=null cm=null
imp= 46 chars=1599 paras=11 rx=null cm=null
imp= 48 chars=1855 paras=12 rx=null cm=null
```

Impressions `median 48, mean 81`, range `46-167`. Own-post band:
**1599-1855 chars, 11-13 paragraphs.**

**Reactions parse as `null` on every post even though the counter element is
present.** Impressions and comment counts extract; reactions do not. The 3
reactions on the top post seen in a manual read did not survive the automated
extractor. Do not build a ranking on the reaction column — it looks available
and silently returns nothing.

## Do not fabricate a post from an unmeasured claim

A queue scaffolder that emits `TODO` wherever material is missing produced
4-of-4 TODO on its first run, because the research file held 3 stale angles
from a single author. **That is the correct behaviour.**

The failure mode is the opposite one — padding a scaffold to look finished,
which puts an invented number into a post about being honest. **An unfilled
slot the owner can see is worth more than a plausible-looking one they cannot
check.**

When asked to "write a post from what we have", the honest deliverable is the
draft *plus the list of facts that are missing*, not a draft that hides the gap.
Five impressions readings and a length band justify a *structure* claim. They do
not justify a causal claim about what makes posts perform.
