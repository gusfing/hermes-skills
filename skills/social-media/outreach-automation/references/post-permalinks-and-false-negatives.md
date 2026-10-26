# Post permalinks, and the two ways a dashboard lies about them

Session 2026-10-01. Asked repeatedly, in four forms: *"add link to the post what
is cards"*, *"create a dashboard where you add post link for evry comment and
like you do in both"*, *"host the dashboard"*, *"give password aswell"*.

Three separate bugs hid behind one request. Each is a general trap.

---

## 1. A permalink is in the `href`, never in the visible text

The X post-confirm path found the new post correctly but recorded
`status: null` for every single post, so no dashboard could ever link one:

```python
body = pg.evaluate("()=>document.body.innerText||''")
if key in body:
    m = re.search(r"/%s/status/(\d+)" % HANDLE, body)   # ALWAYS None
    return True, (m.group(1) if m else None)
```

X renders the status id **only as an href attribute**. It is never text a user
sees, so a body-text search can never match it. Read the attribute instead:

```js
(h => {
  for (const a of document.querySelectorAll('article')) {
    for (const l of a.querySelectorAll('a[href*="/status/"]')) {
      const href = l.getAttribute('href') || '';
      if (href.indexOf('/' + h + '/status/') === 0) {
        const m = href.match(/\/status\/(\d{15,25})/);
        if (m) return m[1];
      }
    }
  }
  return null;
})(HANDLE)
```

Two details that make it correct rather than merely working:

- **Filter on our own handle.** An article's links include quoted posts and
  retweets. Without the `href.indexOf('/'+h+'/status/') === 0` guard, a quoted
  post supplies the wrong id.
- **Take the FIRST `/status/` link, never "find any".** A measured article's
  link list looks like
  `['/Kunalsharmadec6/status/2105266733640716321', '/Kunalsharmadec6/status/2105266733640716321/analytics']`
  — index 1 is the analytics tab for the same post. `.find()` over a loose
  filter can hand you the wrong element.

Verified once written: HTTP 200 per URL, and each loaded page carried the exact
source text. `https://x.com/i/status/<id>` 307-redirects to
`https://x.com/<handle>/status/<id>` — that redirect is normal, not an error.

## 2. A backfill that matches on a short prefix attaches the wrong URL

Matching a recorded post to a profile article on a 30-character prefix matched
**both** posts to the wrong permalinks. Both had to be reverted to `null` and
re-matched on a ~70-character slice of whitespace-flattened text.

```python
flat  = " ".join(text.split())     # posts contain newlines; the feed renders spaces
needle = flat[:70]
for a in arts:
    if needle[:55] in a["text"] and a["id"]:
        ...
```

Backfills are not self-verifying. Treat "it found a match" as a hypothesis and
require the *content check* before writing.

## 3. Then the verifier was the thing that was broken

The first verifier reported `MISMATCH` on both URLs. It was wrong, and acting on
it would have destroyed correct data.

Cause: on a permalink page the article had not rendered within `settle=8`, so
the article list came back **empty**, and the comparator searched an empty list:

```
MISMATCH 22_contrarian.txt  https://x.com/.../2105574405061685478
  expected: Nobody wants more content. They want t
  page has: (no article)          ← the probe's own output, ignored
```

The probe printed the evidence that it had checked nothing. Re-ran with a 25s
settle: both `OK`, `articles=1`, text present.

**The rule: a verifier that reports a failure must print what it actually saw.**
An empty or zero-element comparison is a probe failure, and a probe failure is
not evidence about the data. This is the same class as the redis `ENOTFOUND`
from a bad argument and the paise/ruppee amount bug — but it is worse in one
respect, because here it was about to trigger a *write* that removes data.

## 4. Truncation hides rows without any error

Both posts had correct URLs, `activity()` returned 133 rows in 24h, and the
web view showed no `posted` rows at all. Nothing was broken in the data path.

The renderer sliced `out[:limit]` with `limit=30`, newest-first, and the posts
were 5h old. Raising to 60 still dropped them — by **48 seconds**.

```python
for lim in (30, 60, 200):
    rows = activity(24, lim)
    print(lim, len(rows), sum(1 for r in rows if r['act'] == 'posted'))
# 30  → 0    60 → 0    200 → 2
```

When a specific expected row is missing from a summary, **sweep the limit before
blaming the data path.** Print the row count at several limits; a row that
appears at one limit and not another is a truncation, not a bug. Set any
activity/table default generously (250 here) and re-derive it from a measured
row count rather than a round guess.

## 5. A dashboard field can go stale and contradict the live source

`dashboard.py` rendered WhatsApp as `unreachable` for a full day. Live:

```
GET /api/health           → 200
127.0.0.1:2785            → LISTEN
docker ps                 → openwa-api  Up 25 hours (healthy)
GET /api/sessions/<id>    → status qr_ready, phone None
```

The channel was up. The **session** had never paired. One cached field said
"channel dead" and was wrong about the thing the user actually needed to know.

- Derive channel status from a live probe in the same command that renders it.
- A channel being *reachable* and an account being *usable* are separate facts.
  Report both: `API up, session qr_ready (never paired)`.
- Never write a health field from a remembered value. A dashboard that lies
  about being broken costs more debugging time than one that says nothing.

## 6. Guessing a symbol name in a secrets module

`from secrets import API_MASTER_KEY` → `ImportError`. The real name was
`OPENWA_API_KEY`. Read the module before importing from it:

```bash
grep -E "^[A-Z_]+ *=" secrets.py
```

Unchanged rule, worth restating because it keeps costing time: never guess an
identifier, a field name, or a key.

---

## LinkedIn: no permalink exists in the feed DOM (measured, exhausted)

Probed 2026-10-01 on a live feed. A "card" is a `div[componentkey]` whose
`innerText` starts with `Feed post`. Inside one card:

| probe | result |
|---|---|
| anchors per card | 10–25 |
| anchors matching `/feed/update/` | **0** |
| `urn:li:activity:` anywhere in the DOM | absent |
| timestamp anchor `href` | `/` |
| timestamp anchor after expanding the card | `null` |

Selectors that return 0 and are *wrong*: `div.feed-shared-update-v2`,
`article`, `[data-id]`, `.occludable-update`, `button[aria-label*="Like"]`,
`button[data-control-name]`, `[aria-label="Reply"]`.

The activity id is materialised only by navigating to the post. Getting links
therefore means opening every engaged post — minutes per post, and it wrecks the
engagement flow. So the extractor returns `""` by design and the dashboard prints
**why** the LinkedIn rows have no link, rather than an empty column. "This cannot
be obtained, here is the measurement" is a better answer than a blank, and stops
the next session re-running the same five probes.

If a future session genuinely needs LinkedIn links, the cost is a separate slow
follow-up pass — not a change to the engagement path.