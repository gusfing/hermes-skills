# LinkedIn feed engagement DOM + transport (2026-09-30)

Selectors measured on a live account. Four "obvious" selectors return 0 on a
page where the element is plainly visible.

## Transport

Playwright's `connect_over_cdp()` uses a **browser-level** websocket and
enumerates every target before finishing the attach. On this host that
handshake timed out at 45s-180s repeatedly while Chrome sat idle at 0.6% CPU
with only ~15 targets open.

A plain websocket to one page's `webSocketDebuggerUrl` (from `/json/list`) does
the same work in **0.1s**. Working driver: `cdp.Session`
(`/home/opc/kawaki-outreach/cdp.py`), needs `websocket-client` in the hermes
venv.

One Chrome, many scripts: serialise with a lock file. Concurrent attaches starve
each other, and a killed run leaves the lock behind — a script exiting with no
output usually means a stale lock, not a dead browser.

## Feed selectors

| thing | selector |
|---|---|
| update card | `div[componentkey]` whose innerText starts with "Feed post" |
| reaction | `button[aria-label^="Reaction button state:"]` |
| comment trigger + submit | button whose **innerText** is exactly `comment` |
| comment editor | `document.querySelector('[contenteditable="true"]')` |
| DM composer submit | `.msg-form__send-button` |

The reaction label suffix carries state ("no reaction" vs a count), so one
selector is both the control and the verification.

## Four traps

1. **Action bar has no aria-label.** Like/Comment/Repost carry no
   `aria-label`, no `data-control-name`, empty SVG aria-label. `innerText` is
   the only handle. `button[aria-label="Comment"]` returns 0 on the same page
   where the button is plainly visible.
2. **JS `.click()` is ignored.** The comment trigger needs
   `scrollIntoView({block:'center'})` then a real `Input.dispatchMouseEvent`
   mousePressed/mouseReleased at the `getBoundingClientRect()` centre. A JS click
   yields zero `[contenteditable]` anywhere on the page.
3. **The comment editor is tiptap/ProseMirror** (`DIV.tiptap.ProseMirror`).
   `Input.insertText` is silently ignored — the editor stays empty. Per-character
   `keyDown`/`keyUp` works; verify by reading `innerText` back and comparing.
4. **The composer mounts OUTSIDE the card.** Scope the editor and its submit
   button to the document or a subtree walked ~6 levels up from the editor —
   never to the card. The submit button's innerText is the same string as the
   action-bar trigger, so an unscoped search hits the wrong one.

Selectors that return 0 and are WRONG: `div.feed-shared-update-v2`, `article`,
`[data-id]`, `.occludable-update`, `button[aria-label*="Like"]`,
`button[data-control-name]`, `[aria-label="Reply"]`. LinkedIn re-hashes classes
to `auyl8d`-style tokens — re-measure, never assume.

## Full comment path that reaches HTTP 200

1. `goto("https://www.linkedin.com/feed/")` explicitly after attach.
2. Card: `div[componentkey]` with innerText starting `Feed post`.
3. Comment trigger: button with innerText exactly `comment`.
4. `scrollIntoView({block:'center'})`, then real mouse events at the rect centre.
5. Editor: `document.querySelector('[contenteditable="true"]')` — outside card.
6. Type per-character `keyDown`/`keyUp`.
7. Submit: innerText `comment` scoped to the composer's subtree.
8. Confirm via HTTP 200 on `createComment`.

## Network capture that reversed the conclusion

```
POST .../actions/server-request?sduiid=com.linkedin.sdui.comments.courtesyReminder  -> 200
POST .../actions/component?componentId=...submitCommentButton
POST .../actions/server-request?sduiid=com.linkedin.sdui.comments.createComment      -> 200
```

DOM state at that same moment: body text did not contain the comment, it was
absent from the activity comments tab, the editor sometimes stayed open, and
"Submitting comment" showed in both success and failure. None discriminate.

## Cost of getting this wrong

Four cycles of building ever-more-elaborate DOM verifiers, disabling a working
feature, and reporting "unproven" to the user twice. The defect was the
verifier, not the action.