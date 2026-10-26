# Deleting a LinkedIn post through its control menu — measured DOM, and why three probes looked "broken"

Class: a post went out that should not have, and it must come down. Read-only
until the destructive step; the acting script is dry-run by default and needs
`--confirm`. Measured 2026-10-06/07 over Playwright attached to an already
logged-in Chrome on CDP (no second login; never call `browser.close()` on the
shared session).

Scripts: `li_delete.py` (act), `li_probe_menu*.py` (selector measurement),
`li_verify_deleted.py` (independent witness).

## Synthetic click opens an empty menu

Three probe rounds, same result: clicking the control through CDP/JS `.click()`
produced a menu with `innerText.length: 0` and `childTags: []`. The dropdown
mounts, it just holds no items — the React handler does not run the path a real
pointer does.

**Use Playwright real mouse events over the same Chrome.** `locator.click()`
with the attached browser worked first try, no re-authentication.

## The selectors are not the obvious ones

| element | actual | the guess that returns 0 |
|---|---|---|
| menu trigger | `aria-label="Open control menu for post by Kunal Sharma"` | any `data-testid` |
| menu item | `DIV[role=button].feed-shared-control-menu__dropdown-item`, text `Delete post` | `[role=menuitem]` |
| confirm modal | `.artdeco-modal` (buttons `Cancel`, `Delete post`) | `[role=dialog]` |
| post hook text | `.update-components-text` | the `[data-urn]` wrapper |

The outer `[data-urn]` wrapper's **first line is the screen-reader label
`Feed post number 1`**, so a hook guard reading the wrapper matches the wrong
string and refuses on a correct target. Read `.update-components-text`.

## `[role=dialog]` matches a hidden modal and poisons every later lookup

A `dialog: true` read came from a **hidden video.js error modal** (`editorLen:
0`, no controls) — not the composer, which had already dismissed correctly.
Worse: an open modal sets `aria-hidden`, after which `get_by_role(...)` returns
**0 for everything**, including the menu item you just confirmed exists.

- Clear leftovers first: `Escape` → click `Cancel`, then measure.
- Print the post-measure `.artdeco-modal` count so a hidden modal cannot hide.
- When a check contradicts a prior success, suspect the selector scope before
  the platform (same family as the scoped-selector false negative in the main
  SKILL).

## Menu open is a race, not an event

A single fixed 2500 ms wait misses it. Poll up to 5 s for the dropdown to hold
items, retry the open on timeout. The first successful run was one poll loop
away from a "menu is broken" conclusion.

## Verification is a separate script

The actor must not be its own witness. `li_verify_deleted.py` reloaded the
profile and ran four checks per post: the URN absent, the hook string absent
from a fresh page, the surrounding posts still present, and a count check.

- **Absent is weak evidence on its own** — require the post's own gone-marker
  shape, plus a positive control that the rest of the feed still renders.
- Re-reading the same DOM node the actor just removed proves nothing; reload
  first.
- `grep` for the deleted hook across local files will hit *other* post files
  and read as "still there". That happened here: the hit was a pre-existing
  post containing the same sentence. Match against the live page, not the repo.

## Refusal beats recovery

`--expect <hook substring>` makes the script refuse unless the target's text
matches what you believe you are deleting; `--confirm` is the only path that
clicks `Delete post`. Without both it prints the plan and exits 0. Given a URN
and a hook, a mis-targeted delete is impossible to reach by accident.

**Get explicit owner approval first.** This run carried
`DELETE POST YOU POSTED BOTH`. A destructive action on a real profile is never
an inferred permission — and list the exact URNs being removed in the same
message you ask.
