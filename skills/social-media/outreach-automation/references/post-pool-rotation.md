# Post-pool rotation and the never-reset tracker

Worked example behind *"You are posting same post daily with no image."* The
complaint looked like a scheduler bug. It was two bugs, in different places,
and the obvious suspect was clean.

## The measurement that ruled out the obvious cause

`assign_posts` looked guilty:

```python
def assign_posts(slots, pool, used):
    avail = [p for p in pool if p.name not in used]
    if len(avail) < len(slots):
        avail = pool          # exhausted -> allow reuse rather than skipping a slot
    picks = random.sample(avail, min(len(slots), len(avail)))
    while len(picks) < len(slots):
        picks.append(random.choice(pool))
```

Tested it directly at three exhaustion levels rather than reading it:

| pool used | slots needed | distinct picks |
|---|---|---|
| 0 / 23 | 10 | 10 / 10 |
| 15 / 23 | 10 | 10 / 10 |
| 20 / 23 | 10 | 10 / 10 |

**No within-run repeats, ever.** Fixing the picker would have changed nothing
and looked like progress.

## The actual cause: a tracker nothing ever clears

`x_used.json` is append-only. Nothing rotates it — not on a pool-length cycle,
not daily. At the time of the audit it held **18 of 23** pool files, leaving 6
available for 10 daily slots.

Next-day plan generated and checked against the tracker:

```
picks already in x_used.json : 8 of 10
```

So 80% of tomorrow's posts were files the user had already seen. The timestamps
looked fine. The spacing looked fine. Every symptom was a scheduling artefact
and the defect was in the state file.

## The fallback turns "too few posts" into "same post again"

With 6 available and 10 slots, `avail = pool` refills from everything. The
inline comment says it plainly: *"exhausted -> allow reuse rather than skipping
a slot."* That is a deliberate trade — and it is the wrong trade whenever the
user is complaining about duplicates. Skipping a slot is invisible; a repeat post
is not.

Two correct behaviours, and the choice belongs to the user because it sets their
repetition tolerance:

- **Rotate** — clear the tracker on a cycle equal to the pool length. Every post
  is used once before any repeat appears.
- **Skip** — when `available < slots`, post fewer and leave the rest unscheduled.
  Zero repeats, fewer posts.

What is never right is the silent refill.

## Check before reporting any schedule

```python
pool = {p.name for p in POOL_DIR.glob("*.txt")}
used = set(json.load(open(USED_FILE)))
available = pool - used
picks = [os.path.basename(s["file"]) for s in plan]
reused = [p for p in picks if p in used]
print(f"available={len(available)} slots={len(picks)} reused={len(reused)}")
```

A plan can look clean on timestamps, spacing and ordering while still being 80%
repeats. Those three numbers are the ones that catch it.

## Watch for a second tracker

The poster defaulted to `/tmp/x_used.json` while every caller passed the repo
`x_used.json`. Two files, two histories, and a reboot wipes the one in `/tmp`.
When two artifacts both claim to track the same thing, one of them is lying —
find which by checking what the callers actually pass, not what the default says.

## A `--plan` flag that only plans today

The scheduler exposed only `--plan` / `--send` / `--run-now`, all wired to the
current date. Asked to show *tomorrow's* posts, it printed today's and wrote
those picks into the plan file — 6 of the 10 slots had already passed by the
time it was rendered.

"Show me tomorrow" was answered with a table that looked right and was entirely
for the wrong day, which is worse than saying the feature does not exist. When a
date-relative view is requested, confirm the dates in the output before
presenting it, and say plainly when the tool can only produce today.
