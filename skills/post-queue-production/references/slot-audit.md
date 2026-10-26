# Slot audit - the one-pass check before handover

Assert the deliverable in one block rather than checking each property as you
build it. Every rule in the SKILL.md body exists because one of these
assertions caught something real.

## What to assert

```python
import json, sys
from pathlib import Path

ROOT  = Path("/home/opc/kawaki-outreach")
state = json.loads((ROOT / "studio_state.json").read_text())
slots = state["slots"]

lis  = [s["linkedin"] for s in slots]
errs = []

# band: measured from the owner's own published posts, not a guideline
for i, t in enumerate(lis, 1):
    if not 1599 <= len(t) <= 1855:
        errs.append(f"slot {i}: {len(t)} chars outside 1599-1855")

# distinctness - the rule that failed when only hooks were varied
if len(set(lis)) != len(lis):
    errs.append("duplicate posts across slots")

# image - owner said "Can you add images yourselves"
for i, s in enumerate(slots, 1):
    if not s.get("image"):
        errs.append(f"slot {i}: no image")

# placeholder - owner said "YOU HAVE TO REPLACE"
if "TODO" in json.dumps(slots):
    errs.append("placeholder shipped")

print("WARNINGS", len(errs))
for e in errs:
    print("  -", e)
sys.exit(1 if errs else 0)
```

## Image must be real bytes, not a filename

A slot can carry `image: "01.png"` while the bytes never landed. Confirm both
ends - the state entry AND that the server serves it - then check magic bytes
so a zero-byte body or an auth-failure HTML page cannot pass as an image:

```python
raw = urllib.request.urlopen(url, context=ctx).read()
assert raw[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
```

## What each assertion has caught

- **length band** - drafts filled from a template landed at 1703 and 1163
- **distinctness** - all slots identical; then hooks-only variation failed too
- **image present** - slots scheduled with `image/NN.jpg` placeholders, no bytes
- **`TODO`** - queue generated from a 3-angle research file with no usable angle
- **tz from db** - expected London `09:07 -> 09:07 UTC`; it was BST, `08:07 UTC`
- **PNG magic** - would have let a 401 body pass as the image

## The band is measured, not authored

`1599-1855` derives from the owner's own published posts (their impression-
weighted shape), not from a LinkedIn best-practices list. Re-derive it when the
underlying post set changes. Do not treat it as a universal constant.

For the zone-conversion half of the audit - expected times computed from
`zoneinfo`, never hand-written - see `timezone-aware-scheduling`.
