# Automated posting: cadence, media, and "it looks the same" reports

Class of task: a scheduler posts from a fixed content pool on a timer, and the
user reports *"you are posting the same post"* or *"no image"*. Both reports are
checkable, and answering them requires care — one was half right, and the real
defect sat next to it.

## Check the claim before agreeing or disputing it

The instinct is to defend. Measure first — the claim is either right, wrong,
or (as here) right about one thing and pointing at the wrong one.

```python
# 1. distinct content actually posted today, from the state file
st = json.loads(Path("x_state.json").read_text())
for p in st["posted"]:
    print(p["t"], p["kind"], p.get("file"))

# 2. how many distinct files, and how much of the pool is left
pool = [p.name for p in Path("x_pool").glob("*.txt")]
used = set(json.loads(Path("x_used.json").read_text()))
print("pool", len(pool), "used", len(used), "unused",
      [n for n in pool if n not in used])
```

Here it showed 7 genuinely distinct posts — so "same post" was wrong — but the
same read surfaced the actual bug: three feed posts inside 22 minutes while the
timeline reported those slots as `skipped`. **Report the measurement, not the
defence, and let the correction point at the real defect.**

## Read state timestamps as UTC unless proven otherwise

State files often store `"2026-10-01T03:46:00"` with no zone, produced by a
script running on a UTC host. Sorting them against `datetime.now()` on a local
box silently reorders the day and makes a clean schedule look bursty. Convert
explicitly before drawing any conclusion about spacing:

```python
IST = timezone(timedelta(hours=5, minutes=30))
ts = datetime.fromisoformat(rec["t"]).replace(tzinfo=IST).timestamp()
```

## The reuse fallbacks are the real cadence bug

Two functions decide *what* to post when the pool is thin, and both make reuse
the graceful-degradation path:

```python
def pick(pool, used, exclude=()):
    fresh = [p for p in pool if p.name not in used and p.stem not in exclude]
    return random.choice(fresh or [p for p in pool if p.name not in used] or pool)
    #                                        ^^^^ reuse       ^^^^^^^^^^ any post

def assign_posts(slots, pool, used):
    avail = [p for p in pool if p.name not in used]
    if len(avail) < len(slots):
        avail = pool     # exhausted -> reuse rather than skip a slot
```

The final `or pool` means exhausting the pool produces **repeats instead of
pausing**, and `assign_posts` pads short picks by re-drawing from the whole
pool. A user watching the timeline will absolutely call this "posting the same
post" — and they are right about the behaviour even when the specific post
differs.

The floor is therefore not enforced by the picker but only by a separate
min-gap check in the caller. When the picker can draw anything and the floor
lives elsewhere, any caller that forgets the floor bursts. Prefer a pool-size
check that **refuses to post** over one that silently reuses:

```python
avail = [p for p in pool if p.name not in used]
if len(avail) < len(slots):
    print(f"[plan] only {len(avail)} unused of {len(slots)} slots -> post fewer")
    slots = slots[:len(avail)]      # drop slots, never widen the pool
```

## Head-slicing a pool starves it silently

The sibling bug in a connection-request batcher: `people[start : start + limit]`
always takes from the **head** of the list. Once the head entries are spent or in
cooldown, every tick computes an empty batch — no error, no ledger row, exit 0.
The job looks perfectly healthy while sending nothing.

Filter the whole pool by eligibility *first*, then slice:

```python
pool = load_pool()
sent = {...}
people = [p for p in pool if key(p) not in sent and not in_cooldown(p)]
batch = people[args.start_index : args.start_index + args.limit]
```

Report the **eligible** count, not the batch size — `pool=204 eligible=162
batch[0:5]=5`. A zero batch is indistinguishable from success without it, and
log the eligible count on every tick so a future zero is visible.

Corollary for daily caps: a limiter function that is *defined but never called*
is worse than an absent one, because it reads as coverage in a file listing.
`grep -c sent_today` and report the call count. And count from the audience's
midnight, not naive local — on a UTC host, "local midnight" is 05:30 IST.

## Persist the schedule; do not rebuild it from random each tick

A plan built by `build_plan()` re-rolled every slot time on each call, and the
due-check compared against those freshly rolled times, so a scheduled post could
never fire at its own minute. Persist with an audience-local day stamp, and
discard anything that is not today's:

```python
data = {"day_ist": ist_day().date().isoformat(), "slots": [...]}
if data.get("day_ist") != ist_day().date().isoformat():
    return None          # stale -> rebuild, never fire at yesterday's times
```

**A format change needs a migration path.** The pre-existing plan file was a bare
list with no `day_ist`, so `data.get(...)` raised. Discard the legacy shape
explicitly (`isinstance(data, list) -> return None`) and rebuild — never infer the
day of an unstamped plan.

Proof is a **two-call differential**: build, wait a second, build again, print
both. Identical times across calls is the evidence; "I added persistence" is not.

## Day boundaries: the plan key and the due-check must agree in one zone

Plan built for the audience's calendar day, due-check against naive UTC, and
between 18:30–21:30 UTC those are *different dates* — so `[plan] nothing due`
every tick, silently, while the log looks like a normal quiet run.

One helper, used by every caller:

```python
IST = timezone(timedelta(hours=5, minutes=30))
def ist_today():
    return datetime.now(IST).date().isoformat()
```

Print both keys side by side when you verify (`plan 2026-10-04` vs
`naive UTC 2026-10-03`) — the mismatch is the bug, made visible.

## Attach media to every post, and prove it

Text-only posts read as low-effort. Resolve art **by stem beside the content**
(`x_media/<pool-name>.png`) so adding art is dropping in one file with no code
change:

```python
media = HERE / "x_media" / (Path(slot["file"]).stem + ".png")
r = x_post.post(pg, text, slot.get("community"), media if media.exists() else None)
```

The platform's own file input is the only reliable attach mechanism, and the
preview node is the only proof — see the Media upload section of `x-automation`.

**Verify coverage for every content item, not a sample.** A partial mapping
posts text-only for the rest and looks like the feature is intermittently
broken:

```bash
for f in x_pool/*.txt; do n=$(basename "$f" .txt)
  [ -f "x_media/$n.png" ] || echo "MISS $n"; done
# must print nothing
```

Note when grepping the result: `ls | grep -v _` silently filters every file if
the naming convention contains underscores. Count with a pattern that matches
the extension instead.

**Audit the claim before you copy it into the code.** A comment here read "only 8
of 23 pool files have art"; measurement showed **23 of 23**. Comments rot — when
a fix is predicated on coverage being partial, verify it and correct the comment
in the same change.

## Do not force a post to prove a feature works

Asked to demonstrate the media path, the last post was 20 minutes old against
a 90-minute floor. The correct move is to **say so and let the scheduler do it** —
verify the wiring by resolving the mapping for upcoming slots instead:

```python
for s in slots[:6]:
    m = Path("x_media") / (Path(s["file"]).stem + ".png")
    print(s["at"], Path(s["file"]).name, "->", m.name, m.exists())
```

Overriding the pacing rule to showcase a capability reintroduces exactly the
burst the floor exists to prevent, and the demonstration is not evidence the
scheduler works anyway.

## State files under /tmp are a countdown

A prospect pool stored **only** in `/tmp/li_pool.json` is on a 10-day fuse:
`/usr/lib/tmpfiles.d/tmp.conf` cleans that directory at `max_age=10d`, and no
script regenerated the file. Check the age before quoting it as a fact, and copy
it next to the code that uses it:

```bash
/usr/lib/tmpfiles.d/tmp.conf | grep -n max_age
ls -l /tmp/li_pool.json          # 4.3d old at 42,081 bytes -> dies at ~10d
cp /tmp/li_pool.json ./li_pool.json && cmp /tmp/li_pool.json ./li_pool.json
```

Keep a fallback path so neither copy is a single point of failure, and report
the verified byte size of both.

## Generated media needs a visual check before it ships

See `x-automation` for the full workflow. The one-line version: **models invent
text even when told not to**, so `vision_analyze` every image ("any readable
words? yes/no first") and regenerate failures before anything reaches a public
post. A fabricated brand name in an attached image is a published mistake.