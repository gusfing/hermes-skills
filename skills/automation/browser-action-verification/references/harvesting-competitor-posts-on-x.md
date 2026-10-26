# Harvesting competitor posts from X when profiles will not render

Measured 2026-10-03 against a logged-in session via raw CDP. Three route facts,
each proven rather than assumed, and each one invalidates an obvious approach.

## 1. Profile pages render nothing

`x.com/<handle>` returns **0 `<article>` elements and 0 `a[href*="/status/"]`**.
Always. Scrolling does not help (`window.scrollBy` x4 still 0). The page shell
loads — title `Profile / X`, a guest-looking body with the footer links and no
session chrome.

Control that proves it is the route and not the session: **`x.com/home` rendered
7 articles and showed no "Log in"** in the same session. So authentication is
fine and the profile route specifically is dead.

A third control: **the owner's own profile rendered 5 articles.** So it is not
"profiles are dead" — it is that *other people's* profile timelines do not
render. Do not generalise this into "X blocks scraping"; broad search on the same
session returns 6-8 articles per query with no challenge.

**Consequence: competitors cannot be read from their profiles. Stop trying.**

## 2. `from:<handle>` returns 0 and it means nothing

| query | result |
|---|---|
| `from:levelsio` | 8 articles |
| `from:dickiebushell` | "No results" — and his profile page was reachable |
| `from:javaburn` | 0 articles |

**A zero from `from:` is not proof an account is inactive, renamed, or missing.**
Two of my three sample handles produced nothing for reasons unknown, and I had
invented that handle list from memory rather than researching it — six of seven
did not exist.

## 3. Topic search works reliably

`https://x.com/search?q=<topic>&src=typed_query&f=top` — 6-8 articles per query,
no captcha, no rate-limit challenge, across 5 consecutive queries in one run.
Allow ~12s settle and poll for results rather than reading once; results render
late. Space queries ~3.5s apart.

**This is also better research.** Searching the *topic* surfaces competitors you
did not know existed, which is the actual goal. A handle list only ever returns
the handles you already had.

## Build the scraper on topic queries, not handles

```python
QUERIES = [
    '("agency" OR "agency owner") (AI OR automation) min_faves:40 -filter:replies',
    '("build in public") (MRR OR revenue OR "first customer") min_faves:30 -filter:replies',
]
url = ("https://x.com/search?q=" + q.replace(" ", "%20")
       + "&src=typed_query&f=top")
```

Poll for `article` elements up to 4 times, 2.5s apart. Halt the whole query if
body text matches `captcha|verify you are human|rate limit` rather than grinding
through a challenge.

Capture per article: text, permalink (`/i/status/<id>`), handle, likes, replies,
views.

## Parsing: strip metadata before you measure anything

Scraped text looks like:

```
Olly @helloitsolly · Sep 30 Lots of founders are crashing out ... Show more 311 294 2.6K 366K
```

Three separate strips are required, and **two of them break on realistic input**:

1. Trailing stat block: `((?:[\d.,]+[KkMm]?\s+){2,4}[\d.,]+[KkMm]?)$`
2. Display name + handle — a `^\S+\s+@handle` prefix fails on **two-word display
   names** ("Iric Midel", "MAX @MaxGrant__")
3. The date, which sits **immediately after the `·`**, not at the end:
   `^(?:[A-Za-z0-9_ .\-]{1,40}?\s)?@\S+\s*·\s*(?:(?:Jan|…|Dec)\s+\d{1,2}(,\s*\d{4})?|\d+[hdmw]|\d{4})\s*`

**If the date survives, every post contains a digit.** The tell is a
`has number in hook / no number in hook` split returning `18 / 0` — I hit this
twice before checking the strip.

View-count parse must tolerate stray `.` and `,` tokens: a bare `float()` raises
`ValueError: could not convert string to float: '.'`. Anchor it:
`^([\d]+(?:\.[\d]+)?)([KkMm]?)$`.

## What the numbers said

25 posts, 23 accounts, 18 with a parseable view count.

| signal | n | median views |
|---|---|---|
| number in first 140 chars | 8 | **6,300** |
| no number | 10 | **1,950** |
| no engagement CTA | 13 | **5,400** |
| has CTA | 5 | **2,000** |
| 250-400 chars | 9 | **5,400** |
| 150-250 chars | 7 | **2,900** |

CTA regex:

```python
CTA = re.compile(r"(drop (it|a|your|the)?\s*(below|your (below|hi))"
                 r"|looking to #?connect|let'?s connect|comment below"
                 r"|drop a comment|who else|connect and grow)", re.I)
```

Bait-vs-clean **medians**: 2,450 vs 5,700 = **2.3x**. The mean gap is 11.7x and
is entirely one 366K outlier — report the outlier in the mean column, never
folded into the ratio.

Duplicate detection: `difflib.SequenceMatcher` on normalised bodies. Two posts
read as "word for word" scored **0.88** — a copy with edits. Quote the ratio.

## Trap: static pool files average 153 chars

The pool being replaced: 23 files, mean 153 chars, **zero numbers, zero named
tools, zero named people.** It sits in the worst length bucket (150-250, median
2,900 views) and fails the strongest predictor (number in hook, 3.2x). Category
commentary cannot compete with a number.