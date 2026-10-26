# X DOM pitfalls — measured, not assumed

Every selector here was read out of the live DOM over CDP, not guessed. When a
selector stops matching, re-measure it (`Accessibility.getFullAXTree` →
`DOM.getBoxModel`) before rewriting logic around it.

## 1. Promoted reply marker

**What happened.** A thread pull ranked replies by likes. The top results were
an ad reading "Bouncer — Tired of thirst traps…" at 5,929 likes, another at
1,696 likes ("WhatsApp numbers"), and a third at **15,947 likes** ("Claude can
WHAT?"). None were replies. Ranking by likes alone hands you promoted units
as the top takes.

**Discriminator.** Walk ancestors from the reply node:

```js
a.closest('[data-testid="placementTracking"]')   // truthy => promoted
```

Real replies have no such ancestor. Also compare against the thread: a reply
whose like count is 2–3 orders of magnitude above everything else is promoted
until proven otherwise.

**Symptom that exposes it.** The report quotes an ad as "the sharpest take
from the other side". The giveaway in the data was engagement numbers that
did not fit the thread's distribution.

## 2. Permalink vs inline `/status/` link

**What happened.** Harvesting a post's permalink returned
`x.com/unclebobmartin/status/…` for a post authored by `fraserpricee`. The
tweet text contained an inline link to the quoted tweet, and
`a.querySelector('a[href*="/status/"]')` matched it first.

**Fix.** The permalink is the anchor wrapping `<time>`:

```js
const t = a.querySelector('a[href*="/status/"] time');
const link = t ? t.closest('a') : a.querySelector('a[href*="/status/"]');
```

**Always verify before citing.** Open each URL you plan to hand over, load
the page, and read back author handle + first line of text. 6/6 cited URLs
were checked this way; one earlier candidate had to be re-fetched because the
page had not rendered inside the wait window — an empty result is not a
failure, retry with a longer wait before concluding anything.

## 3. Engagement counters

**Raw strings measured on the search results page:**

```
aright group '45 likes'   -> aria-label  "45 Likes. Like"
aright group '3.1K views' -> aria-label  "3,100 views. View post analytics"
aright group '45K views'  -> aria-label  "45,127 views. View post analytics"
```

**Bug.** A parser that took the *visible* text `45 Likes`, stripped non-digits
to `45 K`, then applied the `K` multiplier returned **45,000** — producing
`45,000 likes on 3,100 views`. Impossible, and that impossibility is what
caught it.

**Fix.** Take the leading integer of the aria-label, ignore the rendered
abbreviation entirely:

```js
const m = (aria || '').match(/^([\d.,]+)\s/);
const n = m ? Number(m[1].replace(/,/g, '')) : null;
```

**Invariant to assert before reporting:**

```python
assert views >= likes, 'views < likes => parser inflated a counter'
```

## Test discipline for this class

- Extract the real helper functions from the shipped script (do not paste a
  hand-written copy into the test — the copy can be correct while the shipped
  code is not). Run them under `node` against raw DOM strings captured above.
- Prove the test fails: re-inject the original bug, expect a non-zero exit.
  If the test still passes with the bug present, it is measuring nothing.
- Guard scripts must **glob** the files they check. A hand-maintained
  whitelist silently stops matching when paths change, prints PASS, and
  covers zero files — that happened here with a 13-entry list that had
  drifted out of every file it claimed to check.
- `$?` after a pipeline reads the last command's status. Capture the exit code
  from the program you actually mean, not from `tail`.

## Running the harvest

- Background every browser-driving script: `nohup … > log 2>&1 &`, then poll.
  A foreground hang previously destroyed a tab set.
- Wait for the status page to render; 6 s is not always enough for a slow
  load. Re-fetch before declaring a URL dead.
- Replies vary between fetches (pagination + ranking). Bump the scroll budget
  when the first pass returns thin takes, and treat any single fetch as a
  sample rather than the thread.
