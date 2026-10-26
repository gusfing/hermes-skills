# Rehearsing and cleaning up a LinkedIn composer (measured)

Measured 2026-10-12 on a live account driven by raw CDP on
`http://127.0.0.1:9222`. The theme: **every step of "close the composer and leave
nothing behind" reported success while doing nothing.** Each entry is a real
run, not a hypothesis.

## Why this matters more than it sounds

A rehearsal (`--stage`) types the *real* post text into the *real* composer and
stops one click short of publishing. If the cleanup fails, the browser is left
holding an owner-approved post in a live composer. That is one stray click —
from the owner, from a later run, from anything that touches that tab — from an
unintended publish.

So the cleanup is not a nicety. Treat "rehearsal left state behind" as a **P1
defect in the rehearsal**, and prove cleanliness from outside the script.

## Failure 1 — the close control has no button text

The original matcher:

```python
CLOSE_JS2 = """
(()=>{
const b = Array.from(document.querySelectorAll('button,[role=button]'))
  .find(x => /discard|close|cancel/i.test((x.textContent||'').trim()));
if (b) { b.click(); return 'closed'; }
return 'nothing to close';
})();
"""
```

On `/sharing/compose` this finds nothing. The control that closes the page is
`aria-label="Dismiss"` with no useful `textContent`. The function returns a
clean-looking string, the script logs "closing WITHOUT posting", and the
composer stays open.

Fix — match all three attributes:

```js
const label = x => ((x.getAttribute && (x.getAttribute('aria-label') || '')) + ' '
                  + (x.title || '') + ' ' + ((x.textContent || '').trim())).trim();
const b = Array.from(document.querySelectorAll('button,[role=button]'))
  .find(x => /dismiss|discard|^close$|^cancel$/i.test(label(x)));
```

Return which control matched (`'closed via: ' + label(b).slice(0, 40)`) so the
next reader can see the match instead of trusting it.

## Failure 2 — dismissing does not clear

After a successful dismiss, LinkedIn **restores the draft into the feed's inline
composer**. A follow-up probe found the editor on `/feed/` still holding all
1064 characters. Closing the composer is not cleaning it.

## The ordering that actually works

Both orderings were measured, on the same text, in the same session:

| order | command | outcome |
|---|---|---|
| clear then dismiss (composer open on `/sharing/compose`) | `execCommand('delete')` | `ok=false`, **1064 chars survive** |
| same, plus `Page.bringToFront` first | `execCommand('delete')` | `ok=false`, **1064 chars survive** |
| dismiss → `bringToFront` → clear (restored `/feed/` draft) | `execCommand('delete')` | `ok=true`, **1064 → 1** |

So: **close first, bring the page forward, then clear.**

```python
s.ev(CLOSE_JS2)
time.sleep(2.0)
log(f"discard prompt: {s.ev(CONFIRM_DISCARD)}")   # /^(discard|leave)$/i
time.sleep(1.5)
s.send("Page.bringToFront")                       # backgrounded tab drops execCommand
time.sleep(0.8)
log("emptying restored draft: " + str(s.ev(CLEAR_EDITOR)))
time.sleep(1.0)
```

The clear itself — CDP key events did not work here: `Input.dispatchKeyEvent`
with ctrl+A then `Delete` left all 1064 chars in place, twice. Range-select plus
`execCommand` did it in one call:

```js
const e = document.querySelector('.tiptap.ProseMirror[role=textbox]');
e.focus();
const sel = window.getSelection(); sel.removeAllRanges();
const r = document.createRange(); r.selectNodeContents(e); sel.addRange(r);
let ok = false;
try { ok = document.execCommand('delete', false, null); } catch (err) {}
return 'cleared=' + ok + ' len=' + ((e.innerText || '').length);
```

`Page.bringToFront` was the difference between `ok=false` and `ok=true` on the
restored draft. `document.hasFocus()` read `true` in **both** cases, so it is not
a usable proxy — issue the call unconditionally.

## Two "is it closed?" checks that are both wrong

**`[role=dialog]`.** The page contains a hidden video.js
`vjs-error-display vjs-modal-dialog`. A dialog count therefore reads true on a
page where every real modal is gone, and a clean dismissal gets logged as
`STILL OPEN`. (The same hidden modal already broke a deletion flow by setting
`aria-hidden` — see `linkedin-deleting-a-post.md`.)

**Editor presence.** On `/feed/` the inline composer's
`.tiptap.ProseMirror[role=textbox]` always exists, so `!!querySelector(editor)`
is true whether or not anything is staged.

The check that works measures text, trimmed:

```js
[...document.querySelectorAll('.tiptap.ProseMirror')]
  .filter(e => (e.innerText || '').trim().length > 0).length   // 0 = clean
```

Trim, because ProseMirror keeps a trailing newline: an untrimmed length of `1`
was reported as `!! draft still present` on an actually-empty editor.

## The composer is a page, not a modal

`modal_count: 0` while `editor_present: true` and the URL is
`/sharing/compose`. Any probe scoped to a modal finds nothing and reports the
composer as absent. Read the URL, not the modal.

## What the image input accepts

```
accept: image/jpeg,image/png,image/gif,image/webp,image/avif,image/bmp
multiple: true
```

**Images only.** A scan of the open composer for document/PDF affordances found
`hasDocumentWord: false`, zero document hits, and media controls limited to
`Media`, `Video`, `Photo`. LinkedIn's document (carousel) post is not reachable
from this composer, so when an owner says "I'll send an image or a PDF", the PDF
has to be converted (page 1 → PNG) or handled through LinkedIn's own UI.

## Proving the attach rendered, not just that the input took the path

`input.files.length` proves the input accepted a path. The rendered preview is a
separate fact, and at this stage the two together are still not proof the post
publishes with the image — only the live post is (see
`browser-action-verification`).

Measured on a good attach:

```
file: {accept: "image/jpeg,image/png,...", multiple: true, files: 1,
       names: ["01.png:103646"]}
blobImgs: 2 → [{w: 700, h: 336}, {w: 158, h: 196}]
bodyHasFileName: false        # the filename is NOT rendered as text
```

The preview is a `blob:` image. Match on `src.startsWith('blob:')` and require a
plausible size; do not search page text for the filename — it is not there, and
that check reports a successful attach as a failure.

Also: the **Photo button** matches `/^photo$/i` on text, and `Upload from
computer` may return `'none'` as a *benign* result when the input mounted on its
own. Treat `Upload button: none` as a signal to proceed to the input poll, not
as a failure.

## A rehearsed run must not be its own witness

After the fixes, the rehearsal logged `REHEARSAL CLEAN — nothing left staged`.
The confirmation came from a **separate** script reading the live DOM:

```json
{"editors": 1, "editorsWithText": 0, "blobImgs": 0, "dialogs": 0}
```

and exited non-zero if any was dirty. A script's own success line is a claim,
not evidence — especially here, where four consecutive versions of that line
were wrong.

## Dead CDP target after a long-lived browser

```
RuntimeError: CDP target 'https://www.linkedin.com/feed/' does not answer
Runtime.evaluate — dead tab, not a site block
```

After ~4 days of uptime the single LinkedIn tab had gone deaf. The session and
login were fine. Open a fresh tab rather than restarting Chrome (restarting
loses the profile's live session):

```bash
curl -s -X PUT 'http://127.0.0.1:9222/json/new?https://www.linkedin.com/feed/'
```

The same error is described in the "hangs" style: stay on the plain
websocket, do not reintroduce `connect_over_cdp`.
