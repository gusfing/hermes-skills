# Google Forms: clicking radios that refuse every synthetic event

Session case log. Four approaches failed on Google Forms radio groups; the
fifth worked. Useful beyond Forms — the same escalation ladder applies to
any React component that uses delegated `jsaction` handlers.

## The symptom

Radio options exist and are visible:

```
document.querySelectorAll('[role="radio"]').length   -> 17
```

but after clicking, every one of them still reports:

```
[role="radio"][aria-checked="true"]                   -> []   (empty)
```

Text inputs in the same form fill fine. Only the radios are dead.

## What failed, in order

1. **`el.click()` on the `[role="radio"]` div** — `aria-checked` stayed
   `false`. The div is not the handler target.
2. **CDP `Input.dispatchMouseEvent` at the div's centre coordinates** —
   nothing. A `scrollIntoView` before the read did not take effect, so
   coordinates were stale/off-screen (y-values came back negative and every
   target resolved to the same y, a strong sign of stale rects).
3. **`dispatchEvent(new MouseEvent('click', {bubbles:true}))`** — nothing.
4. **Clicking the parent `<label>`** — nothing, even though the label is
   582px wide and 24px tall, i.e. clearly the intended hit area.

## Why: `jsaction` delegation

The real markup carries a delegated handler:

```html
<div role="radio" aria-label="Male" data-value="Male"
     jsaction="keydown:I481le;dyRcpb:dyRcpb;click:cOuCgd; mousedown:UX7yZ; ...">
```

`jsaction` means Google's framework binds the listener at an ancestor and
dispatches by event name. The 20x20 circle is a **decorative child**; the
`aria-checked` value is managed by that framework, not by the DOM node's own
attributes. Synthetic events never satisfy it.

Also note the inner structure — the 20x20 circle resolves to a
`div.d7L4fc` with no role and no label, wrapped in
`div.bzfPab` (64x24) then `label.docssharedWizToggleLabeledContainer`
(582x24). Targeting any single layer fails.

## What worked

Use the **accessibility tree** to get real backend node IDs, then the real
input pipeline:

```python
nodes = cdp("Accessibility.getFullAXTree")
# filter role == "radio" and name in target labels
# -> [('Male', 148), ('Undergraduate', 250), ('3', 322), ('No', 388)]

for label, nid in targets:
    q = cdp("DOM.getBoxModel", backendNodeId=nid)["model"]["content"]
    x = int((q[0]+q[2]+q[4]+q[6]) / 4)
    y = int((q[1]+q[3]+q[5]+q[7]) / 4)
    cdp("Input.dispatchMouseEvent", type="mouseMoved",     x=x, y=y)
    cdp("Input.dispatchMouseEvent", type="mousePressed",   x=x, y=y, button="left", clickCount=1)
    cdp("Input.dispatchMouseEvent", type="mouseReleased",  x=x, y=y, button="left", clickCount=1)
```

Two details that matter:

- **Source coordinates from the AX node**, not from a `getBoundingClientRect()`
  on a DOM selector. The AX node's box is what the input pipeline will hit.
- **Send `mouseMoved` first.** Some handlers ignore a press/release pair
  with no preceding move.

Re-read `[aria-checked="true"]` after **each** click, not once at the end.

## Generalisation — the escalation ladder

When a click does not register, go up one rung and never repeat a rung:

1. Playwright element handle `.click()` (dispatches trusted-ish events,
   does its own actionability checks)
2. `.click(force=True)` — skips overlay interception
3. AX tree + `DOM.getBoxModel` + full mouse move/press/release
4. Keyboard: focus the element, then `Space` / `Enter` — often the cheapest
   fix, since `jsaction` lists `keydown` handlers too
5. Stop and hand the control to the user in noVNC

**Verify by reading state after every single interaction.** Batching four
clicks then checking once tells you only that at least one failed, not which.

## Consent gates

A consent/"I agree" radio is the first item on most study forms. Clicking it
on a user's behalf consents *them* to something. If the form is a research
instrument, read the questions and flag the consent step to the user before
crossing it — do not click through a research ethics attestation because it
is in the way.

## Related

- `references/x-post-workarounds.md` — the X posting case log
