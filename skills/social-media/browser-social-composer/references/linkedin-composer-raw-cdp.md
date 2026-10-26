# LinkedIn composer via raw CDP (measured)

Measured 2026-10-05/06 against a real logged-in account driven by raw CDP on
`http://127.0.0.1:9222`. Everything below was read off the DOM, not inferred.
The X sections of this skill do not transfer — LinkedIn's composer differs.

## The five facts that decide the job

| thing | reality |
|---|---|
| login probe | **`[global-nav]` does not exist** (`globalNav:false`). Every other container candidate is false too — only `<main>` is true. |
| "Start a post" | a **DIV** with `role=button` and an **empty `aria-label`**. `querySelectorAll('button')` never finds it. |
| the editor | `.tiptap.ProseMirror[role=textbox]`, contenteditable. There is **no `<textarea>`**. |
| file input | mounts only after clicking **`Upload from computer`**, ~3s later. Not before. |
| verifying the attach | `input.files.length`. Not any `img` count. |

## Login check

`[global-nav]` is what most LinkedIn automation reaches for. It is absent, so
that check reports "not logged in" for a session that is perfectly fine, and
the automation aborts before doing anything. Measured on `/feed/`:

```
.tiptap=false  article=false  [role=main]=false  [role=feed]=false
[global-nav]=false  .feed-shared-update-v2=false  [role=banner]=false
main=true
```

Use what measured true:

```js
document.title.includes('LinkedIn')
  && !location.pathname.startsWith('/login')
  && !!document.querySelector('main')
```

Keep it as **one string literal**, not three concatenated fragments. A
fragment-by-fragment syntax check sees three pieces each under its length
floor and verifies nothing.

## Open, type, and what the controls really are

All of these live under `button,[role=button]`. Match on `textContent`, not
`aria-label` — the important ones have none.

- **Start a post** — DIV, text `Start a post`. Opens a `[role=dialog]` with a
  `.tiptap.ProseMirror[role=textbox]` inside.
- **Photo** — DIV, text `Photo`. Clicking it changes the URL to
  `/sharing/compose`.
- **Upload from computer** — a real **BUTTON**, appears in the panel after the
  Photo click and stays stable for ~24s.
- **Post** — text `^(post|publish)$`, `disabled === true` while the body is
  empty. Check it before clicking, not after.

Set the body through the tiptap editor, dispatching a real input event:

```js
ed.focus();
ed.innerHTML = text.replace(/\n/g, '<br>');
ed.dispatchEvent(new InputEvent('input', {bubbles:true, inputType:'insertText'}));
```

`session.ev()` evaluates an *expression*, so a top-level `return` throws
`SyntaxError: Illegal return statement`. Wrap every multi-statement block in an
IIFE — `(()=>{ ... })();` — not a bare arrow.

## The file upload, in order

The step that cost the most time: **the input does not exist until you click
`Upload from computer`.** Probing for `input[type=file]` straight after the
Photo click returns 0, which looks exactly like "LinkedIn has no file input
here". It is there, later.

```
Start a post (DIV)
  -> set text in .tiptap.ProseMirror
  -> Photo (DIV)                    url becomes /sharing/compose
  -> Upload from computer (BUTTON)  input[type=file] mounts in ~3s
  -> DOM.setFileInputFiles(nodeId)
  -> verify input.files.length > 0
  -> Post
```

```python
root = s.send("DOM.getDocument", depth=-1)["root"]["nodeId"]
nid  = s.send("DOM.querySelector", nodeId=root,
              selector="input[type=file]")["nodeId"]
s.send("DOM.setFileInputFiles", files=[str(img)], nodeId=nid)
files = s.ev("document.querySelector('input[type=file]').files.length")
```

Poll and re-set rather than setting once: an early set can land before the
input is ready, and a one-shot attempt will never retry. On success the file
input carries `accept: image/jpeg,image/png,image/gif,image/webp,image/avif,image/bmp`
and `multiple`.

**Check the CDP response of `setFileInputFiles`.** It returns `{}` on success
and an `error` key on failure; ignoring it turns a rejected upload into a
silent no-op.

### A disproved hypothesis, recorded so it is not re-tried

`DOM.getDocument()` defaults to `depth=1`, so I suspected the shallow tree was
hiding a deep `input[type=file]` from `DOM.querySelector`. It was not: on the
same page state the pure-JS count and the CDP lookup returned **0 and 0** —
they agreed, so the lookup was never the problem. The input genuinely was not
mounted yet. Two agreeing signals beat one plausible explanation.

## Playwright was tried first and bought nothing here

`chromium.connect_over_cdp("http://127.0.0.1:9222")` reuses the same Chrome
and profile, so there is no second login — but it adds nothing for this
composer and introduces two traps:

- `browser.close()` would kill the real browser. Only ever `playwright.stop()`,
  which detaches the driver and leaves the browser running.
- `page.get_by_role("button", name="Upload from computer")` returned **0** while
  the raw JS text match found the button. Role+name matching is stricter than a
  substring scan, and this control's accessible name is not wired the way the
  matcher expects. Prefer a raw-JS `innerText` scan.

Use Playwright for file choosers that are genuinely native; here the input is
real DOM, so raw CDP is simpler and already attached.

## Verify the attach on the input, not on a preview

The first working run reported `file set but no image preview appeared` — for a
run that had **in fact attached the file**. The check was
`[role=dialog] img`, which stayed at 0 the entire time, while the document's
`img` count went **26 -> 30**. The selector was scoped to a container that
never contains the preview.

The reliable signal is the input itself:

```js
document.querySelector('input[type=file]').files.length   // 1 after a good set
```

Never conclude from one selector. Take two independent readings — `files.length`
plus the document-wide image delta — and require them to agree before
reporting.

## Rehearse before publishing, and keep publish separate

A posting script that can only fully publish or do nothing cannot be tested
without publishing. Three modes, in increasing danger:

| mode | does | guard |
|---|---|---|
| dry run (default) | prints plan: chars, image, hook | exits before touching the browser |
| `--stage` | opens, types, attaches, confirms Post enabled, then **closes** | never reaches the submit click |
| `--publish` | the only path that clicks Post | refuses on empty text or `TODO` in the copy |

Refuse rather than continue when a precondition fails — posting without the
image is the failure mode worth avoiding. The stage run that proved this path
ended with `attached, input.files.length=1` and `composer dismissed: yes`.

## Attribution when something appears that you did not send

A post matching the staged draft was found live on the profile. I could not
prove who published it, and said so rather than guessing.

What *was* provable is worth extracting: the live post had **no image**, and
the publish path attaches and verifies an image before it will click Post. So
a completed `--publish` run cannot produce a text-only post — that route is
excluded on the code's own terms, independent of who did the clicking.

**Exclude your own path structurally, then state plainly what remains
unknown.** A publish gate that aborts on a missing image is proof the no-image
post did not come through it; it is not proof of who did publish it. Do not
close that gap with an assumption.

Check for leftovers afterwards — an aborted run can leave a composer open with
real text in it. Navigate away, then confirm `dialog: false`, `editorLen: 0`,
`fileInputs: 0` before calling the session clean.

## Diff against the draft, not against memory

To confirm a live post is yours, pull its full text and diff it against the
source file rather than eyeballing it:

```python
difflib.unified_diff(slot.splitlines(), live.splitlines(), lineterm='', n=1)
```

Two gotchas, both hit here:

- LinkedIn renders each hashtag as its own block, so a post stored as
  `#a #b #c` reads back as three lines plus a blank. Strip the UI label
  (`hashtag\n`) before comparing, or a byte-identical post looks edited.
- The permalink route
  (`/feed/update/urn:li:activity:<id>/`) is a SPA that may render **nothing** to
  automation — no `<time>`, no post text. Read the post from
  `/in/<handle>/recent-activity/all/`, which does render. The
  `urn:li:activity:<id>` is still the stable identifier to quote.

`<time>` comes back empty on the activity page too, so a timestamp is often
simply not obtainable — say so rather than inferring one from file mtimes.
