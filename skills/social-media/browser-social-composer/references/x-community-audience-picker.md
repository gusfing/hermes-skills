# X Community Audience Picker — session case log

Working path for posting into an X Community from a browser session.
Discovered 2026-09-29 after first reporting the feature as broken.

## The failure that caused the wrong conclusion

```python
r = cdp("Runtime.evaluate", expression="""
    [...document.querySelectorAll('[data-testid$="addAudience"]')].length
""")
# -> 0
```

Zero matched, and I concluded community posting was broken. Wrong. The
audience control exists and has **no `data-testid`**. Every `data-testid`-based
search for it returns 0 forever.

The revealing probe was dumping every control in the composer scope and
printing `aria-label`:

```python
btns=[...scope.querySelectorAll('button')].map(b=>({
  txt:(b.innerText||'').trim(),
  aria:b.getAttribute('aria-label')
})).filter(x=>x.txt||x.tid||x.aria)
# -> [{'txt': 'Everyone', 'tid': None, 'aria': 'Choose audience'}]
```

One `data-testid` column in that dump would have found it instantly. Always
print `aria-label` alongside `data-testid`.

## Verified sequence

```python
POST = "..."  # 358 chars in the verified run

pg.goto("https://x.com/home", wait_until="domcontentloaded")

# 1. wait_for_selector, NOT a bare query_selector — at 7s the composer is
#    often still absent and .click() raises AttributeError on None
el = pg.wait_for_selector('[data-testid^="tweetTextarea"]', timeout=45000)
el.click()

# 2. audience button: aria-label only, no data-testid
ab = pg.wait_for_selector('button[aria-label="Choose audience"]', timeout=25000)
ab.click()
pg.wait_for_timeout(4000)

# 3. community rows are [role="menuitem"] in a virtualized grid.
#    Scanning menuitemradio / option / button finds nothing.
target = None
for m in pg.query_selector_all('[role="menuitem"]'):
    if (m.inner_text() or "").strip().startswith("Build in Public"):
        target = m
        break
print("menuitem found:", bool(target),
      (target.inner_text() or "").replace("\n", " | "))
# -> menuitem found: True Build in Public | 267.9K Members

# 4. force=True is mandatory — [data-testid="mask"] intercepts pointer events
#    and a normal click dies with "subtree intercepts pointer events" after 30s
target.click(force=True)
pg.wait_for_timeout(3500)

# 5. read the audience back BEFORE typing and again before submitting
cur = (pg.query_selector('button[aria-label="Change audience"]')
       or pg.query_selector('button[aria-label="Choose audience"]'))
print("AUDIENCE NOW:", (cur.inner_text() or "").strip())
# -> AUDIENCE NOW: Build in Public

# 6. type, then check for an in-flight submit
pg.query_selector('[data-testid^="tweetTextarea"]').click()
pg.keyboard.type(POST, delay=40)
```

## The disabled Post button

Immediately after staging 358 chars with the audience correctly set:

```
audience at send time: Build in Public
chars staged: 358
NO POST BUTTON
composer after send: 358
```

The button was **not missing**. A DOM dump showed:

```python
{'txt': 'Post', 'tid': 'tweetButtonInline', 'aria': None, 'dis': True, 'w': 67}
```

`dis: True` — a submit was already in flight from the earlier click. My
loop reported `NO POST BUTTON` because it tested `if el and not el.is_disabled()`,
and an in-flight button is *disabled by design*.

Polling 6x at 5s intervals showed it stayed disabled with text still staged:
not a successful publish, and not a normal idle state either.

**Rule:** `disabled: True` on `tweetButtonInline` with text staged means a
submit is in flight. Poll the composer char count and the disabled flag. Never
loop re-clicks, and never log `NO POST BUTTON` off a disabled-button branch —
it is a submit-in-progress signal, not a missing button.

## What was NOT resolved

The audience selection was verified (`AUDIENCE NOW: Build in Public`, 358
chars staged) but the final publish was not confirmed. The Post button stayed
disabled for 30+ seconds. Untested from here:

- whether a hard reload of `/home` lets the same sequence complete cleanly
- whether a second community post is blocked while the first is pending
- whether the post carried a community link (the definitive check)

If you are picking this up: redo the sequence from a fresh `/home` load, confirm
`tweetButtonInline` is **enabled** before typing, then verify via the author
profile for an `a[href*="/i/communities/"]` link inside the `<article>`.

## Related trap: brand account

The session browser was logged in as `@Kunalsharmadec6` (personal). The
notifications feed showed **"Kawaki Studios"** posting as a *separate account*
(its own posts, its own likes). Confirm which account the user wants posting
from before running this — the audience picker is per-account, and the joined
community list belongs to whoever is logged in.

## Selector summary

| Target | Selector | Has testid? |
|---|---|---|
| Composer | `[data-testid^="tweetTextarea"]` | yes |
| Audience button | `button[aria-label="Choose audience"]` | **no** |
| Community row | `[role="menuitem"]` (in `cellInnerDiv`) | no |
| Post button | `[data-testid="tweetButtonInline"]` | yes |
| Modal mask (blocks clicks) | `[data-testid="mask"]` | yes |
| Post→community proof | `article a[href*="/i/communities/"]` | no |
