# X Posting, Community Targeting, and Reply Automation

Measured on a live logged-in desktop Chrome over CDP (`connect_over_cdp`),
2026-09-29. Every selector below was read out of the live DOM, not inferred.

## Why the audience control is easy to miss

The post-to-community control carries **no `data-testid` at all**. Searching for
a `data-testid` containing "audience" returns 0 matches and it looks like the
feature is absent. It is found only by its `aria-label`:

| Element | Selector | Reads |
|---|---|---|
| composer | `[data-testid^="tweetTextarea"]` | — (`tweetTextarea_0` on `/home`) |
| audience button | `button[aria-label="Choose audience"]` | `Everyone` |
| after selecting | `button[aria-label="Change audience"]` | the community name |
| community rows | `role="menuitem"` | community name + `N Members` |
| row container | `[data-testid="cellInnerDiv"]` | virtualized grid |
| post button | `[data-testid="tweetButtonInline"]` | `Post` |

**Always read the audience label back after selecting** and before typing. That
one string is the only proof the post is scoped:

```python
cur = (pg.query_selector('button[aria-label="Change audience"]')
       or pg.query_selector('button[aria-label="Choose audience"]'))
audience = (cur.inner_text() or "").strip()   # must equal the intended community
if audience != intended:
    raise SystemExit("audience not set")
```

## Three traps, each of which produced a wrong conclusion

1. **Community rows are `role="menuitem"`, not `menuitemradio` or `option`.**
   They render inside a virtualized `[data-testid="cellInnerDiv"]` grid, so a
   scan for the semantically "expected" role finds nothing and the feature reads
   as missing. Match on `inner_text().startswith(name)`.

2. **Rows require `click(force=True)`.** A `[data-testid="mask"]` overlay
   intercepts pointer events; a normal click times out after 30s having done
   nothing. Same shape as a sticky nav dropdown swallowing a click — if a click
   is visible, enabled, stable, and still fails, suspect an overlay before
   suspecting the app.

3. **A `disabled` post button is a stuck composer, not a failed post.** Check
   `is_disabled()` *before* typing text. If text is staged and the button is
   already disabled, reload the page — it does not recover on its own in 30s+.

## The left community tab rail is a filter, not the audience

The joined-community list in the left rail looks exactly like an audience
selector. Clicking a tab only changes the feed shown. Posts made that way go to
the personal timeline with **no community attached** and no error. This is the
single most convincing wrong path: the post succeeds, the UI implies the
community, and nothing in the response says otherwise.

Detect it afterwards by checking the post's own article for an
`/i/communities/` link. A post with no such link is personal-timeline only.

## The reply-dialog collision

Replying is **not** the same DOM as posting, and the collision is silent:

- The **home composer is also `[data-testid="tweetTextarea_0"]`**. A global
  query for it types into the feed *behind* the reply modal. The dialog's Reply
  button then stays `disabled` forever, and the click returns no error. Nothing
  is posted and nothing reports failure.
- The dialog's submit button is `[data-testid="tweetButton"]`, **not**
  `tweetButtonInline`.

Always scope both to the dialog:

```python
dlg = pg.query_selector('[role="dialog"]')
box = dlg.query_selector('[data-testid="tweetTextarea_0"]')
btn = dlg.query_selector('[data-testid="tweetButton"]')
```

**A real dispatch closes the dialog.** That is the cheapest available
confirmation — poll for the dialog going away rather than trusting the click:

```python
btn.click()
pg.wait_for_timeout(3000)
if pg.query_selector('[role="dialog"]'):
    pg.keyboard.press("Escape")   # did not dispatch; do not count it
```

## Confirmation is asynchronous — poll, do not check once

Measured: a post was **invisible at 6s and visible at 39s**. A single check
produces a false negative, which then gets reported as a failed post and
retried, producing a duplicate.

Poll the feed a few times before concluding anything:

- posts → `/HANDLE` (replies live under `/HANDLE/with_replies`)
- match on the **first 40 chars of the first line**, which is stable
- on a miss, say "dispatched only" — never "failed" and never "posted"

Note that community feeds may render **0 `<article>` elements** on a
desktop session while the profile feed renders normally. Absence of articles on a
community page is **not** evidence the post is missing; it is a rendering gap.
Confirm placement from the profile feed and the audience label, and state that
community-feed placement is unverified rather than inferring either way.

## Search URL that returns usable results

```
https://x.com/search?q=<query>%20-filter%3Areplies%20lang%3Aen&src=typed_query&f=top
```

`-filter:replies` drops reply-chains you cannot add to. `lang:en` is essential —
without it a large share of results are non-English and unusable. `f=top` is
the tab worth targeting for engagement.

`f=live` returns **0 articles** on a fresh desktop session. If articles are
missing, switch to `f=top` before concluding the account is rate-limited.

## Reply quality bar

Filler replies are worse than none and are the main thing that gets an account
flagged. Banned openers: `great post`, `love this`, `nice one`, `following`,
`dm me`, `opportunity`. Pull a concrete proper noun out of the target post and
reference it — the specificity is the whole point, and a templated reply reads
as templated.

Stop the run immediately on captcha/challenge. Retrying through one is the
fastest route to a locked account.
