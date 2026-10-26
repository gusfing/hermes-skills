---
name: x-research
description: Use when researching X/Twitter conversations, read-only.
---

# x-research

Harvest and analyze X without touching the account's engagement surface. This
is the class "what is actually happening on X right now, and who is saying
what" — distinct from posting (`x-automation`), outreach (`x-outreach`) and
content-idea sweeps built on a paid MCP (`audience-radar`).

**Read-only by standing rule.** No like, repost, follow, reply or post. A
research session that engages has broken the owner's `only posting, no
comments` directive and burned browser trust in the same move. Loading a post
page is fine; clicking anything in its action bar is not.

## Route

Prefer, in order: an installed X CLI if one exists; the general web search
tool; **then the logged-in browser over CDP**. The browser route is the one
that reliably works when the other two are unavailable, and it is what this
skill documents.

Connect Playwright over the existing Chrome CDP endpoint rather than launching
a new browser — a fresh profile means a fresh login, and login is the whole
reason this route is valuable. Drive it from the project venv, and
**background every browser command with a log file and a poll.** A foreground
browser hang has killed a whole tab set before; a stuck script should cost a
poll, not a session.

## Three measurements that lie

These are not hypotheticals. Each one shipped a wrong answer in this session
before it was caught. Full selectors and reproductions in
`references/x-dom-pitfalls.md`.

### 1. Promoted replies sit inside the reply list

Thread pulls rank replies by like count. Promoted posts are injected into that
same list and carry **engineered like counts** — one captured ad showed
**15,947 likes** and would have been quoted as the sharpest rebuttal in a
debate report, above every real person. The tell is an ancestor carrying
`data-testid="placementTracking"`; real replies have no such ancestor.

Always filter on it, then sanity-check the survivors: a reply whose like count
is orders of magnitude above every other reply in a thread is a promoted
unit until proven otherwise.

### 2. The first `/status/` link is rarely the permalink

On a search results page and especially on a status/conversation page, the
first `a[href*="/status/"]` inside a post is an **inline link in the tweet
text** or the **quoted tweet**, not the post's own URL. This returned Uncle
Bob's permalink for a post *about* Uncle Bob — a citation pointing at the
wrong person entirely.

The permalink is the one wrapping a `<time>` element. Prefer it:

```js
const t = a.querySelector('a[href*="/status/"] time');
const link = t ? t.closest('a') : a.querySelector('a[href*="/status/"]');
```

### 3. Engagement counters abbreviate, and naive parsers inflate

The visible counter reads `45K`; the accessible label reads
`"45 Likes. Like"`. A parser that strips non-digits then applies the `K`
multiplier to the aria text reports **45,000 likes** — which surfaced as
`45,000 likes on 3,100 views`, an impossibility that was the only reason the
bug was visible.

Parse the **leading integer of the aria-label** and ignore the rendered
abbreviation. Then assert the invariant before reporting anything:

```python
assert views >= likes, f'views {views} < likes {likes} — parser is wrong'
```

Never publish a number that has not survived that assertion.

## Prove the parser with a test that can fail

A self-check that re-runs the shipped code against the shipped output proves
nothing. Extract the real parsing helpers and run them in isolation against
**raw strings measured from the live DOM**, then inject the original bug and
confirm the test goes red. A test that still passes when the bug is
reintroduced is not a test — it is a green light with no bulb.

## Before you cite a link

Open every URL you are about to hand over and confirm it resolves to the
author and post you claim. A `curl -s -o /dev/null -w '%{http_code}' -L`
beats guessing; for the ones that need a rendered page, load it and read the
handle and first line back. This catches the permalink bug above and any
hand-assembled identifier.

## Reading a thread honestly

- Pull replies more than once. Pagination and ranking shift between fetches, so
  a set captured on one scroll is not "the thread" — it is a sample. Deeper
  scrolls change which takes you find.
- Rank by likes for the headline, then read for the sharpest wording. The
  highest-liked reply is often a restatement; the sharp one is usually further
  down and less popular.
- Report both sides with attribution and number. A debate write-up that quotes
  only the side you agree with is advocacy, not research.
- Views on a status page may not render for posts that are not yours. Take
  views from the search harvest where they are reliable, and say which source
  a number came from when it matters.

## Related

- `grounded-post-writer` — turning what you found into a post that cites it
- `audience-radar` — the paid-MCP route to the same class of question
- `no-comments-guard` — the engagement prohibition this skill obeys
