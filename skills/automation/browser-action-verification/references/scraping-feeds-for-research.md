# Scraping social feeds for research: dead routes and silent failures

Session 2026-10-02. Task: "use agent reach and fetch posts from my competition."
The data came out, but three separate failures nearly produced confident wrong
conclusions. All three are verifier-shaped, not tool-shaped.

## Route table — X, logged-in Chrome via raw CDP

| route | result |
|---|---|
| `x.com/<handle>` (other people) | **0 articles, 0 `/status/` links, always.** Renders a ~497-char guest shell (footer only). Scrolling 4x does not help. |
| `x.com/<own handle>` | 5 articles — session logged in, DOM reads fine |
| `from:<handle>` in search | **Unreliable.** 8 articles for one handle, "No results" for another whose profile page is reachable |
| **topical search** `x.com/search?q=...&f=top` | **6-8 articles, no challenge, handles + permalinks intact** |

**A zero from a profile page tells you nothing.** Same for `from:`. Both look
like "account inactive" or "account does not exist" and neither is established.
Before concluding an account is dead or missing, prove it with a second route.

Workable route: search the **topic** and capture whoever returns. That also finds
competitors you didn't know existed, which is the actual point.

## Failure 1: a raw-CDP evaluate returning `{}` looks exactly like an empty page

`cdp.Session` picked the first tab whose URL contained `x.com`. Every
`evaluate()` then returned `{}` — `readyState: {}`, `html len: 0`,
`innerText len: 0`. I reported this as "attached to a non-answering target."

**It was my own test bug, and then a wrapper bug.**

The test bug: `s.ev('()=>location.href')` — passing a *function literal* over CDP
serializes to `{}`. `{}` here meant "you sent a function, not a call." The real
call was `s.ev('location.href')`.

The wrapper bug, which is the durable part: `ev(expr, default=None)` returned
`default` when a *nested* result was missing, so every probe printed the same
`{}` and a dead tab was indistinguishable from a wrong expression. Fixed by
raising on target-selection failure rather than degrading to a default.

**A sentinel that appears in every failure mode is not a diagnostic.** When one
value keeps showing up regardless of condition, suspect the reporter before the
thing being reported. This is the "verifier that fails on everything is the
suspect" rule in its purest form.

## Failure 2: a handle list written from memory is a fabricated dataset

First run used six handles recalled from an earlier session. Five did not
resolve. The run produced an empty account map that *looked* like "these
accounts are inactive" — a conclusion built entirely on invented input.

**Never enumerate targets from recall.** Search the topic and let the platform
supply the handles. If a specific handle is required, verify it exists first and
report the ones that don't instead of folding them into a null result.

## Failure 3: two claims that survived being wrong

Both were mine, both were published to the user before measurement:

- **"word-for-word identical"** for two near-identical bait posts. Measured
  `difflib.SequenceMatcher` ratio: **0.88**. A copy with edits, not identical.
- **"40x"** for bait-vs-honest performance. That was the best bait post against
  the single best honest post. Medians: **bait 2,450 / no-bait 5,700 = 2.3x**.
  The 2.3x is the defensible claim; 40x is a max-vs-max artefact.

The 366K outlier is real and belongs in the writeup — but it belongs in the
*mean* column (3,133 vs 36,535), not smuggled into a ratio of medians. Report
the statistic that matches the claim you are making.

## Stat extraction from a rendered card

X renders the foot of a card as `replies reposts likes views` with no labels, so
the last four tokens are positional:

```python
tail = re.search(r"((?:[\d.,]+[KkMm]?\s+){2,4}[\d.,]+[KkMm]?)\s*$", text)
nums = [num(x) for x in tail.group(1).split()]   # K/M suffix aware
views, likes = nums[-1], nums[-2]
```

Parseable on 18 of 25 posts. A token like a bare `.` raises `ValueError` in
`float()` — anchor the regex (`^([\d]+(?:\.[\d]+)?)([KkMm]?)$`) rather than
assuming clean input.

**Poll, don't sleep once.** Results render late. Loop the evaluate up to 4 times
with a 2.5s gap before recording "no results."

## Detecting duplication honestly

To check whether two accounts posted the same thing, normalise and measure —
do not eyeball it:

```python
norm = lambda p: re.sub(r"[^a-z ]", "", re.sub(r"\s*@\w+\s*·\s*", " ",
                                   p["text"][:200]).lower()).strip()
ratio = difflib.SequenceMatcher(None, norm(a)[:120], norm(b)[:120]).ratio()
```

Also check whether two accounts share an opening body at all (group on the first
60 normalised chars) — that is how you discover a spam tier that is replicating
itself, which is invisible when you read one post at a time.

## Chatbot shells can be seeded with a query

`min_faves:` floors work on the topic queries and are what separate signal from
engagement-bait spam. In the measured run, 18 of 25 raw hits were bait until the
floor was applied, and the bait accounts were largely posting each other's
templates.

## Reading a card that's truncated

Search results truncate with a **"Show more"** control. The full post is
reachable by navigating to its permalink and reading
`[data-testid=tweetText]` — otherwise you are analysing a summary and will
misjudge its length and structure. The 366K-view post was truncated to 340 chars
in the feed and was ~1,600 chars in full.