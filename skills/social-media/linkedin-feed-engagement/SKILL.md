---
name: linkedin-feed-engagement
description: Use when automating LinkedIn feed likes and comments.
---

# LinkedIn feed engagement — measured DOM (2026-09-30)

Every selector here was measured on a live account. Four "obvious" selectors
return 0 on a page where the element is plainly visible — this is the trap.

## Transport: raw CDP, never Playwright

`connect_over_cdp()` stalls in the `ws connected` handshake and times out at
90–180s while Chrome sits idle at 0.6% CPU. The same handshake over a plain
websocket to the same `webSocketDebuggerUrl` returns in 0.1s. Playwright
enumerates every target before attaching; raw CDP talks to one page.

Working driver: `cdp.Session` in `/home/opc/kawaki-outreach/cdp.py`.
Needs `websocket-client` (installed in the hermes venv).

One Chrome, many scripts → serialise with `cdp_lock.py`. Two concurrent
Playwright attaches both hang.

## Feed selectors

| thing | selector |
|---|---|
| update card | `div[componentkey]` whose innerText starts with "Feed post" |
| reaction | `button[aria-label^="Reaction button state:"]` |
| comment trigger + submit | button whose **innerText** is exactly `comment` |
| comment editor | `document.querySelector('[contenteditable="true"]')` |
| DM composer submit | `.msg-form__send-button` |

Reaction label suffix is the state: "no reaction" → reacted. One selector is
both the control and the verification.

## The four traps

1. **Action bar has no aria-label.** Like/Comment/Repost carry no
   `aria-label`, no `data-control-name`, empty SVG aria-label. `innerText` is
   the only handle. `button[aria-label="Comment"]` returns 0.
2. **JS `.click()` is ignored.** Comment trigger needs
   `scrollIntoView({block:'center'})` first, then a real
   `Input.dispatchMouseEvent` mousePressed/mouseReleased at the button's
   `getBoundingClientRect()` centre. A JS click yields zero `[contenteditable]`
   anywhere on the page.
3. **Comment editor is tiptap/ProseMirror** (`DIV.tiptap.ProseMirror`).
   `Input.insertText` is silently ignored — the editor stays empty. Per-character
   `keyDown`/`keyUp` works; verify by reading `innerText` back and comparing.
4. **Composer mounts outside the card.** Scope the editor and its submit button
   to the document or a subtree walked up from the editor — never to the card.

Selectors that return 0 and are WRONG: `div.feed-shared-update-v2`, `article`,
`[data-id]`, `.occludable-update`, `button[aria-label*="Like"]`,
`button[data-control-name]`, `[aria-label="Reply"]`. LinkedIn re-hashes classes
to `auyl8d`-style tokens — re-measure, never assume.

## Comment submit (verified via network)

Clicking the submit button shows **"Submitting comment"** in some cases, but that is not proof. MEASURED 2026-09-30: the submit POST is
`com.linkedin.sdui.comments.createComment` and returns **HTTP 200** when the comment publishes. The comment **does** persist — the earlier DOM check was wrong.

**Verification that works:** listen for `Network.responseReceived` for the `createComment` URL and require status **200**. Do NOT rely on editor clearance or body text. `Network.getResponseBody` can return `-32000 (No data found for resource)` for that request — ignore it.

Implementation notes: enable Network, drain stale events before clicking, then wait up to 20s for the 200. The editor is tiptap/ProseMirror — use per-character `keyDown/keyUp` (not `Input.insertText`). The submit button is innerText `Comment` with no aria-label, inside the composer's subtree (~6 levels up from the editor); use a real mouse event at its center. JS `.click()` is ignored. The editor may remain mounted after submit — that alone is not a failure.

## DM send (verified)

- Thread rows in the messaging list are click-only divs — **zero anchors**, no
  href, no role. Click `getBoundingClientRect()` coordinates.
- **Enter does not send.** It leaves the text staged. Click
  `.msg-form__send-button` (it is `disabled` until the composer has text).
- Verify by reading the text back out of the thread and confirming the composer
  cleared.

## Verify every action with a control

A render failure is indistinguishable from success. Likes: reaction label flips.
Comments: absent from the comments tab = failed. DMs: text in thread + composer
empty. Never report a send from a click alone.