# Reading conversations on X — harvest, rank, argue both sides, cite verified links

Class of task: "what's trending / what's the debate / sharpest take each side".
Read-only. Nothing here likes, replies, reposts or follows — owner directive is
posting-only, and a research run must never trip it.

Measured 2026-10-07, logged-in desktop session over CDP (Playwright),
`web_search` gateway down. Scripts: `x_trend.py` (search harvest),
`x_thread.py` (replies), `x_probe_ads.py`/`x_probe_ads2.py` (ad marker),
`x_verify_links.py` (citation check), `test_x_trend_metrics.py` (parser self-check).

## The four traps, in the order they cost time

### 1. Promoted replies sit inside the reply list and outrank the real debate

Ranked by likes, the top "replies" to a niche thread came back as ads:
`Tired of thirst traps... Bouncer` at **5,929 likes**, `WhatsApp numbers for
agents` at 1,696, and later a fake `Claude can WHAT?` at **15,947**. Quoting
any of them as the sharpest rebuttal would have shipped a paid placement as the
voice of the community.

The marker is an ancestor with `data-testid="placementTracking"`:

```js
if (a.closest('[data-testid="placementTracking"]')) return null;   // promoted
```

Ads appear in search results too, not only under a post. Filter in the
extractor so ranking happens after, never before.

### 2. Exact engagement lives in `aria-label`, and the label contains a trap

Measured DOM for one post:

| field | `aria-label` | `innerText` | truth |
|---|---|---|---|
| like | `"45 Likes. Like"` | `"45"` | 45 |
| views | `"3174 views. View post analytics"` | `"3.1K"` | 3174 |

Two ways to get this wrong, both shipped:

- **Strip non-numeric characters and you are left with `45 K`** — because
  `Like` contains a `K`. A number parser with an optional `[KMB]` suffix then
  reads that letter as a multiplier and reports **45,000** likes for 45. The
  failure is invisible: 45K is a plausible figure for a viral post.
- **Concatenate `innerText + aria-label` and digit-strip** — you fuse two
  readings of the same quantity into a third number that is neither.

Take the leading exact integer from the label, fall back to text only when the
label is absent:

```js
const ariaCount = s => {
  const m = String(s || '').match(/([\d][\d,]*)/);
  return m ? parseInt(m[1].replace(/,/g, ''), 10) : null;
};
const num = s => {                    // text fallback, suffix must be adjacent
  if (!s) return null;
  s = s.trim().replace(/,/g, '');
  const m = s.match(/^(\d+(?:\.\d+)?)([KMB])$/i);
  if (!m) return parseInt(s.replace(/[^\d]/g, ''), 10) || null;
  return Math.round(parseFloat(m[1]) * {K:1e3, M:1e6, B:1e9}[m[2].toUpperCase()]);
};
```

**Sanity invariant: a post's views cannot be below its likes.** When the
harvest returned 4,179 likes on 3,100 views, the platform was not broken —
the parser was. Re-measure the raw strings instead of reasoning about which
field "should" be right.

### 3. The permalink is the timestamp link, not the first `/status/` anchor

This corrects advice that shipped in both `x-automation` and this skill.
Measured: on a **status page**, the first `a[href*="/status/"]` inside the
article is the inline link in the tweet body, so Fraser Price's post resolved
to `unclebobmartin/status/2105647907705868659` — a real post, the wrong one.
Quoted cards make the same move. The timestamp anchor is the permalink:

```js
const t    = a.querySelector('a[href*="/status/"] time');
const href = t ? t.closest('a').getAttribute('href')
               : (a.querySelector('a[href*="/status/"]')?.getAttribute('href') || null);
```

**Then verify every URL you intend to publish.** Open it, assert the author
handle and a text slice. Six of six passed; a seventh returned an empty author
not because the link was wrong but because 6 s was not enough to render —
re-wait before calling a permalink dead. `https://x.com/i/status/<id>`
307-redirects to the canonical form; that is normal.

### 4. The OP is not the debate

`f=top` gives the viral post, never the argument. Sharpest takes on each side
come from a thread pass: scroll ~16 times or until the reply count stops
growing, sort by likes, then select the top take *per side* — and label sides
from the content, not from reply order (supporting and opposing replies
interleave).

Query shape that worked:

```
"<exact phrase>" since:<YYYY-MM-DD> lang:en      f=top    viral set
<topic> since:<YYYY-MM-DD> lang:en               f=live   fresh set
```

Rank across queries with `score = likes + 2*reposts + replies`, dedupe by
status id, then group by topic by eye. Reply *ratio* is a better signal of a
real argument than absolute size: 168 replies on 148 likes is people arguing,
while 1,795 likes on 145 replies is applause.

## Prove the parser before quoting a single number

`test_x_trend_metrics.py` extracts the JS helpers out of the live script, runs
them through `node`, and asserts against the **exact strings the DOM
rendered** (`"45 Likes. Like"` → 45, `"3,174 views."` → 3174). It must pass,
and it must fail when the K-suffix bug is re-injected — re-inject and confirm
both halves, or the test is decoration.

Its first run failed for a reason that was the *test's* fault: JSON `null`
arrives as Python `None`, and the expectation was written as the string
`"null"`. A test that asserts the wrong type fails for the wrong reason and
then trains you to distrust passing runs. Fix the expectation, not the parser.

## Building these probes

Write probe files with `write_file`. Constructing them inside `execute_code`
via nested triple-quotes mangles escapes: an intended `\n` inside a JS string
literal lands as a **raw newline**, which is invalid JS — and `py_compile` will
not catch it, because Python was never the thing that broke. This bit twice in
one session before the pattern stopped.

Related: `references/harvesting-competitor-posts-on-x.md` (profile timelines
render 0 articles, `from:<handle>` unreliable, topic search works),
`references/what-gets-views-in-a-niche.md` (baseline hooks/lengths).
