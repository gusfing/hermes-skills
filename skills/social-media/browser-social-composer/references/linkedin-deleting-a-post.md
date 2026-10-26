# Deleting a LinkedIn post — measured 2026-10-06

Two posts were deleted on a live account, each verified absent by four
independent readings. This file records the flow that worked and the four
probes that looked right and were not.

Attach to the already-running Chrome so the login is reused:

```python
b = sync_playwright().start().chromium.connect_over_cdp("http://127.0.0.1:9222")
page = next(pg for pg in b.contexts[0].pages if "recent-activity" in pg.url)
# never browser.close() -- it takes the real session with it
```

## Synthetic click opens an empty menu shell

Raw CDP / `el.click()` on the "..." control returns cleanly and produces:

```
menu container: .feed-shared-control-menu__content, artdeco-dropdown--is-open
innerText.length == 0
childElementCount == 0
/delete/i.test(document.body.innerText) === false
```

The dropdown mounts with no children. Two probes documented it
(`li_probe_menu.py`, `li_probe_menu2.py`). Playwright's real `locator.click()`
is what fills it. Do not treat a clean return as an opened menu.

Playwright's click is still not instant: one run saw 0 items at 2.5s and the
same click succeeded when polled. **Poll, and allow a second attempt**
before concluding the menu is unavailable:

```python
for attempt in (1, 2):
    btn.first.click()
    for _ in range(10):
        page.wait_for_timeout(800)
        if item.count():
            break
    if item.count():
        break
```

## Measured selectors

| step | correct | looked right, wrong |
|---|---|---|
| menu trigger | `button[aria-label^="Open control menu for post by"]` inside `[data-urn*="<id>"]` | counting every `button` — aria-labels on feed controls are often empty |
| delete item | `DIV[role=button].feed-shared-control-menu__dropdown-item` with text `Delete post` | `get_by_role("menuitem")` → **0 while the menu is correctly open** |
| confirm | `.artdeco-modal` whose text contains **both** `Delete` and `Cancel`, then `get_by_role("button", name="Delete", exact=True)` | `[role=dialog]` → matches a **hidden video.js error modal**, never the confirm |
| post body for identity | `.update-components-text` inside the container | `container.inner_text()` → first line is the screen-reader label `Feed post number 1` |

The `[role=dialog]` mis-scope is the one that reads most convincingly: the
probe printed `dialog: true` while `editorLen: 0` and `ctrls: []` — a
`vjs-error-display vjs-modal-dialog vjs-hidden` element. A truthy selector
count is not a description of what it found.

## Identity guard before any destructive click

Locate by URN **and** require a known substring of the opening line. Both
posts were dry-run first with `--confirm` absent; the guard refused once
(before `.update-components-text` was used) and correctly stopped on the
screen-reader label rather than deleting.

```python
body = post.locator(".update-components-text").first
hook = body.inner_text().split("\n")[0][:60]
if expect not in hook:
    print("REFUSING"); return 1      # never broaden this to a fuzzy match
```

Dry run first, delete second, on every target, every time.

## A leftover modal makes `get_by_role` return 0 on a live DOM

After a failed attempt the confirm modal stayed open. The next run reported
`menu button count: 0` while the hook still matched — the post was there.
LinkedIn marks the page `aria-hidden` behind a modal, and Playwright filters
`get_by_role()` on accessibility, not on presence.

```python
for _ in range(3):
    if page.locator(".artdeco-modal").count() == 0:
        break
    page.keyboard.press("Escape")
    page.wait_for_timeout(1200)
if page.locator(".artdeco-modal").count():        # Escape not guaranteed
    page.locator(".artdeco-modal").last.get_by_role(
        "button", name="Cancel", exact=True).click()
```

Clear stale overlays **before** measuring anything, or every count afterwards
is about accessibility state rather than the page.

## Verifying the deletion — four readings, not a grep

Reload, then require all four to be false:

1. URN in the set of `[data-urn]` attribute values
2. URN in `document.body.innerText`
3. the full opening sentence in the joined `.update-components-text` texts
4. that sentence in `document.body.innerText`

`posts_on_page` is printed alongside so an empty page cannot masquerade as a
successful deletion (10 posts remained; only the 2 targets went).

**A grep of the probe log is not verification.** Checking the log for
`fastest typers` returned `1` after both posts were gone, because a
pre-existing older post opens `The best developers are no longer the fastest
typers.` — a substring collision with the deleted post's `The best
developers aren't the fastest typers.` Match on the URN, and match on enough
of the sentence that it cannot collide with a neighbour.

## What failed first, in order

1. `[role=menuitem]` → 0 items on an open menu.
2. `[role=dialog]` → found video.js, not the confirm modal.
3. `container.inner_text()` → screen-reader label, guard refused (correctly).
4. single 2.5s wait → menu sometimes not filled yet.
5. no modal cleanup → `get_by_role` 0 on a present element.

Each produced an error, not a wrong deletion. Keep the refusal at the front:
the one thing that must never fail open is the identity check.
