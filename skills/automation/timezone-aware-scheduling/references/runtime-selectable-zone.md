# Runtime-selectable timezone (owner picks the zone in a UI)

Measured 2026-10-04 building a post-queue editor for `/home/opc/kawaki-outreach/`
(`studio.py`). 29/29 checks pass. This is the design that worked.

## The shape

One JSON file holds everything. Slot times are **wall clock in the owner's
chosen zone**, plus the zone name at the top level:

```json
{"version": 1, "tz": "America/New_York", "day": "2026-10-05",
 "slots": [{"id": "01", "at": "09:07", "platform": "x",
            "community": "Indie Hackers", "linkedin": "", "x": "hi",
            "image": "53100f6d32.png"}]}
```

`at` is never converted on write. UTC appears only in the response, for display.

## Why not store UTC

If the owner picks Kolkata, sets 8 slots, then switches to New York:

- stored UTC -> every slot silently shifts by the offset delta, and nothing says so
- wall clock + name -> 09:07 stays 09:07, now meaning 09:07 New York

The second is what a person means when they type 09:07 into a box.

## Verified conversions

`09:07` local, day `2026-10-05`:

| zone | offset | UTC |
|---|---|---|
| America/New_York | -0400 | 13:07 |
| Asia/Kolkata | +0530 | 03:37 |
| Europe/London | +0100 (BST) | 08:07 |
| Asia/Tokyo | +0900 | 00:07 |
| Australia/Sydney | +1100 | 22:07 |
| Pacific/Auckland | +1200 | 20:07 |

## The London trap

First suite run: 25/26, `Europe/London 09:07 -> 09:07 UTC` **failed** (got
`08:07`). London is BST in October. The code was right; the hand-written
expectation was wrong. Fixed by computing expectations from `ZoneInfo` at test
time — see the SKILL.md section. Expect the same failure on any zone with DST
if you hardcode.

## Zone validation

```python
try:
    ZoneInfo(s.get("tz") or "")
except Exception:
    warn.append(f"timezone {s.get('tz')!r} is not a valid zone; saving UTC instead")
```

Name the bad value in the message. `ZoneInfo("Mars/Phobos")` raises
`ZoneInfoNotFoundError`. Never swallow it into a silent UTC fallback.

## Audit findings worth copying

These warnings are cheap and caught real defects on first run:

- slot text still contains `TODO` -> the scaffold outran the material
- LinkedIn length outside the owner's measured band
- X over 280 chars
- slot targets a community but has no X text
- invalid timezone name

Measure the band from the owner's **own** posts, do not assume. Measured here:
1599-1855 chars, 11-13 paragraphs, no CTA, media attached.

## Serving notes

- Bind `127.0.0.1`. Auth in the app, not only nginx — a Cloudflare quick
  tunnel points at the listener directly and never touches nginx (this exact
  hole shipped a dashboard publicly on 2026-10-01).
- Basic auth: 401 with a **zero-byte body** so the password file cannot leak.
- Atomic save: write `.tmp`, then `Path.replace()`. A crash mid-write must not
  truncate the queue.
- Reject an empty slot list outright (400). Otherwise a bad payload silently
  replaces a good queue with nothing.
- Save uploads to a uuid filename; serve only `Path(name).name` under one
  media dir. Verified against 5 traversal encodings, all 404.
- Validate upload by extension allowlist (`.png/.jpg/.jpeg/.webp/.pdf`), not by
  trusting the client MIME type.

## Injecting server data into a JS template

```python
PAGE = PAGE.replace("let S=null, ZONES=[];",
                    "let S=null, ZONES=[];\nconst COMM=" + json.dumps(COMMUNITY_ORDER) + ";")
```

`json.dumps` produces a real JS literal. String-concatenating a Python list
into JS yields `['a', 'b']` with quotes the browser reads as string delimiters
that terminate early — it looks right in the source and breaks at runtime.

## Do not import the schedule module for a constant

Reading `COMMUNITY_ORDER` by importing `x_schedule` dragged in `x_post` ->
`playwright`, so the editor needed a browser installed to show a dropdown.
Read the literal instead:

```python
for node in ast.walk(ast.parse(Path("x_schedule.py").read_text())):
    if isinstance(node, ast.Assign) and any(
            getattr(t, "id", "") == "COMMUNITY_ORDER" for t in node.targets):
        return list(ast.literal_eval(node.value))
```

No import, no dependency graph, and it raises loudly if the constant is renamed
or starts being computed. If it does become computed, this breaks — that is the
intended trade, not a silent fallback.

## Guardrails (enforced)

- 29/29 checks pass (auth, zone math, traversal, uploads, rejection, atomic save)
- Timezone computed from ZoneInfo, never hardcoded
- Zero-byte 401 body; uploads uuid-named; only basename served
- Path traversal blocked across 5 encodings
- Empty slots rejected (400); bad JSON rejected (400)
