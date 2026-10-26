# Review-first calendar UI

Session 2026-10-11. Upgrading `studio.py` (the content calendar at port 8792)
from a flat form list into a slot-card UI with review state. Owner directive:
`YOU LEAVE EVERY THING JUST UPGRADE THE UI OF CONTENT CALLENDER`.

## The pitfall that actually bit: string-anchor injection into embedded JS

The page is one big `PAGE = r"""..."""` HTML string inside `studio.py`. Data the
server owns (the community list) is injected by string-replacing an anchor in the
embedded `<script>`:

```python
PAGE = PAGE.replace(
    "let S=null, ZONES=[];",
    "let S=null, ZONES=[];\nconst COMM=" + json.dumps(COMMUNITY_ORDER) + ";", 1)
```

Rewriting the CSS/JS moved that declaration onto a shared line
(`let S=null, ZONES=[], VIEW='all', OPEN={};`), so the anchor no longer matched,
the replace silently did nothing, and `COMM` was `undefined` at runtime —
community dropdowns would render broken. **Python compilation passes, the page
serves 200, and the JS is syntactically fine. The only witness was the guard.**

Two lessons, both general:

1. **A server-side `str.replace` fails silently.** It is not an exception, not a
   warning, just a page that quietly lost a feature. If a replace injects
   required data, `assert` the anchor was found, or count occurrences after.
2. **Reproduce a failed injection immediately.** Grep the *served* page, not the
   source:

   ```bash
   curl -s -u kunal:"$(cat .dash_pw)" http://127.0.0.1:8792/ \
     | grep -o 'const COMM=\[[^]]\{0,60\}'
   ```

   That one line separated "anchor missing" from "JS broken" in one call. Then
   split the one-line declaration so injection has a clean statement boundary:

   ```python
   old_decl = "let S=null, ZONES=[], VIEW='all', OPEN={};"
   new_decl = "let S=null, ZONES=[];\nlet VIEW='all', OPEN={};"
   ```

   Injecting mid-statement produces `...];, VIEW='all'...` — the guard's
   `node --check` caught that as `SyntaxError: Unexpected token ','`.

## Probe 1 — live DOM, not HTTP status

A 200 plus a JS syntax check both pass on a page that paints nothing. Measure
what rendered (Playwright, sync API, headless):

```python
ctx = b.new_context(viewport={"width": 1280, "height": 1000},
                    http_credentials={"username": "kunal", "password": PW})
page = ctx.new_page()
page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
page.on("pageerror", lambda e: errs.append(str(e)))
page.goto("http://127.0.0.1:8792/", wait_until="networkidle")

out["cards"] = page.locator(".card").count()
page.locator(".card").first.click()          # editor must open on click
out["textareas_after_click"] = page.locator(".edit textarea").count()
out["console_errors"] = errs                  # must be []
```

Exercise every filter and count cards in each — a filter that returns the same
count for `linkedin`, `x` and `all` is wired to nothing.

## Probe 2 — layout by arithmetic, not by screenshot

Overlap and overflow are `getBoundingClientRect` math. A full-page vision pass
**timed out** on this page while the arithmetic answered in one call:

```javascript
// anything left position:fixed is usually an overlay bug
[...document.querySelectorAll('body *')]
  .filter(e => getComputedStyle(e).position === 'fixed')

// pairwise overlap inside one card
for (let i=0;i<els.length;i++) for (let j=i+1;j<els.length;j++)
  if (!(a.bottom<=c.top+1 || c.bottom<=a.top+1 ||
        a.right<=c.left+1 || c.right<=a.left+1)) hits.push(...)

document.documentElement.scrollWidth > window.innerWidth   // horizontal overflow
```

Run it at 1280 / 820 / 390 px. The owner reviews from his phone; a desktop-only
check misses the layout he actually sees.

## Probe 3 — provable-failing review state

`ready` is derived (`body + image + no TODO`), so the guard must prove it reacts
to a real mutation. Mutate through the **server** (not by editing the file), or
you are testing your own JSON writer:

```python
shutil.copy2(STATE, BAK); orig = STATE.read_bytes()
try:
    a = measure()                       # baseline
    s = json.loads(orig); s["slots"][0]["image"] = None
    api("/api/save", s); time.sleep(0.5)
    b = measure()
    assert b[0] == 1, f"needs-me should be 1, got {b[0]}"
    assert b != a, "UI did not change at all"
finally:
    STATE.write_bytes(orig)
    assert STATE.read_bytes() == orig    # restore proven byte-identical
```

Measured result — baseline `(0 needs, 2 ready, 0 needs-image)` → after strip
`(1, 1, 1)`, stats `images 2/2 · ready 2/2` → `images 1/2 · ready 1/2`.
State restored, bytes matched.

## Defects the probes caught that vision had reported vaguely

| Reported | Actual cause | Fix |
|---|---|---|
| "floating badge overlaps content" | `#step` chip pinned `position:fixed` bottom-left | move the value into a stats chip, delete the fixed element |
| "`09:372` looks like a stray time" | UTC value printed bare with `z` appended per row | label once (`title="UTC"`), render `${utc}z` |
| "remove line feels crowded" | — | measured gap 9px, no overlap; nothing to fix |

The third row is the point: two of three visual complaints were real, the third
was not. Measuring turns a subjective screenshot report into a fix list — and the
final `overlapsInCard: []`, `scrollW == viewW` result is evidence a screenshot
cannot give.

## What was deliberately not done (ponytail)

Review state stays **derived**. An explicit `approved` flag is the upgrade path
once the human review loop needs to record a decision that copy+image cannot
infer — not before. No state-file migration was written; old files load
unchanged because nothing was added to the schema.
