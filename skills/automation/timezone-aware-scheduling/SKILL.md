---
name: timezone-aware-scheduling
description: Use when recurring jobs must land in a user's local hours.
---

# Scheduling in the audience's timezone

Class of task: "post 8x/day", "engage every 30 min", "run this between 9 and 5".
The host clock is almost never the audience clock. If the schedule is computed
in server time and only *displayed* differently, the bug is invisible until the
user reads it back at 23:00 local and says "it's 10:55 in Delhi".

## The rule

**Convert at the source.** The generator, not the display layer, must produce
times in the audience's zone. Fixing the output formatting while leaving UTC
slots underneath is a cosmetic patch on a real bug.

```python
from datetime import datetime, timedelta, timezone
IST = timezone(timedelta(hours=5, minutes=30))   # named for the audience, not the host

def now():
    return datetime.now(IST)

def ist_day():
    """Today for the audience. Near midnight UTC it is already tomorrow in
    Delhi, so generating slots from the UTC date builds the wrong day's plan."""
    return datetime.now(IST).date()
```

Print **both** zones afterwards. A plan that only shows IST stops the next
reader from noticing a regression; a plan that only shows UTC is how the bug
ships.

## Do not set TZ for the process

```bash
TZ=Asia/Kolkata python x_schedule.py --plan   # WRONG if the script also prints a UTC column
```

With `TZ` exported, every naive `datetime` renders in that zone, so a script
designed to print "IST | UTC" prints the **same value twice** and the UTC
column silently becomes a lie. Convert explicitly in Python with a real
`tzinfo` instead, and leave the host timezone alone.

## Verify the schedule in the target zone, then stop

The verification that actually catches this is: list the next N fires, convert
them, and check the window. Do this before declaring the schedule fixed.

```python
IST = timezone(timedelta(hours=5, minutes=30))
# parse the timer's NextElapseUSecRealtime, then:
print(dt.astimezone(IST).strftime('%H:%M IST (%a)'))
```

Do **not** do the conversion in shell with `date -u -d '+5:30'` and string
surgery — that was tried and produced an unchanged timestamp with no error.
`strptime` + `.replace(tzinfo=utc)` + `.astimezone(IST)` in Python is the
shortest correct path.

Sanity-check the offset direction once, out loud, in the output: server
`17:25 UTC` must read `22:55 IST`. If it does not, the sign is wrong.

## systemd timers: see `references/systemd-oncalendar-traps.md`

`OnCalendar` is the usual mechanism and it has several silent-failure modes: a
comma hour list fires **once a day** at the last hour, and a `:MM/repeat` spec
parses but yields `Trigger: n/a` and never fires. Both pass
`systemd-analyze --user verify`. Read the reference before writing a timer.

**Ranges are hour ranges.** `03:30..21:30` is invalid syntax, so an audience
window that does not land on the hour cannot be written as a range. Use one
`OnCalendar=` line per time-of-day with a bare reset line first — that is the
documented list idiom, not a mistake.

**Prove the window, do not infer it.** `systemd-analyze calendar` prints only
the *next* elapse, so counting its output reports 1 fire even for a correct
every-30-min spec — that mistake produced a confident, wrong "fires once a
day" call. Read `Normalized form` for every line, and run
`scripts/check_timer_window.py <unit>…` which does it live, also flagging an
empty list and an unarmed `Trigger: n/a`.

## A window that is correct in UTC can still be wrong locally

A range crossing local midnight is contiguous in UTC and looks fine in
`list-timers` output while the audience sees a different day. When the user
names a local window, convert **both edges** and state them in local time in
your reply — the UTC table is for you, the local table is the one that gets
read.

## Mixed-zone pipelines: the bug survives "convert at source"

Converting the generator is necessary and **not sufficient**. A pipeline can
build a correct IST plan and still post nothing, because a *different* layer
makes the due-check.

Measured 2026-10-03 in a posting pipeline (`/home/opc/kawaki-outreach/`):

- `build_plan()` planned slots for `ist_day()` — correct.
- Every "is it due now" comparison used naive `datetime.now()` — **UTC**.
- The state day-rollover key `x_state["day"]` was the **UTC** date.

From 18:30 UTC (00:00 IST) to 21:30 UTC the plan targets *tomorrow* IST while
state tracks *today* UTC. Result: **`[plan] nothing due`, exit 0, every tick.**
Worst possible shape — silent, successful-looking, and inside the exact hours the
timer covers. The post never fires and nothing errors.

**Audit the whole pipeline for zone, not just the generator.** Grep every
`datetime.now`, `date.today`, `utcnow`, and state-day key. Every one of them needs
an explicit `tzinfo`. A file that imports a helper named `ist_day()` and also
calls bare `datetime.now()` is the tell.

### Day rollover is a timezone decision

If the audience day is IST and the state key is `date('now')` in SQLite, the day
flips at 00:00 **UTC** = 05:30 IST — mid-window. Reset-then-post can then post
into the wrong day's counters. Derive the state key from the same `ist_day()` the
planner uses.

## Plan generation must be deterministic and persisted

Same audit, second finding: `build_plan()` called `rnd.randint(0,59)` per slot
with no seed, and **each caller built a fresh plan**. So the schedule never
existed — it was re-randomized on every tick. Proof: two consecutive
`build_plan(day=D)` calls gave different minutes for every slot, and in a
simulated day **29 of 29 posts fired at a time that differed from their planned
time**.

Random jitter is fine. Random jitter that is *redrawn on every read* is not a
schedule. Build once per day, persist it, and have every reader load the same
file. If `plan.json` is written by a manual `--plan` flag and no scheduler ever
reads it, the schedule is decorative.

Also: a ticker that selects a due slot and then shells out to a child that
picks independently has thrown its own selection away — measured: ticker chose
`20_confession.txt`, the child posted `01_confession.txt`.

## When the user picks the zone, the constant is gone

Above, the audience zone is a module-level constant. It stops being one the
moment the owner can choose it from a UI. See `references/runtime-selectable-zone.md`.

Three things change together when a zone becomes runtime data:

1. **Thread `tz` through every layer.** Any remaining `IST = timezone(...)`
   constant is now a silent wrong answer for everyone who picked something
   else. Grep for the old constant before shipping the picker.
2. **Store wall-clock + zone name, not UTC.** `{"at": "09:07", "tz": "Asia/Kolkata"}`
   survives a later zone change correctly; a stored UTC timestamp silently
   shifts every slot by the offset difference. Convert to UTC **at render,
   for display only**.
3. **Re-validate the zone by name on write.** `ZoneInfo(...)` raises on a bad
   name — catch it and warn *with the bad name in the message*, don't fall back
   to UTC quietly. A silent fallback is how a whole queue lands at 3am.

**Write-once, validate twice.** Hand-written test expectations fail on DST
boundaries. Compute expectations from the tz database in tests — if your
assertion differs from `ZoneInfo`, assume your assertion is wrong.

## Serving and security notes for a runtime picker

- Bind to 127.0.0.1. If a quick tunnel can reach it directly, enforce app auth (Basic) even when behind nginx; the tunnel can bypass vhost-only auth.
- Basic auth returning 401 with a **zero-byte body** avoids leaking credential file contents in error bodies.
- Atomic writes (`.tmp` → `replace`) prevent truncation on crash.
- Reject empty collections (e.g. zero slots) outright (400) — never let a bad payload overwrite a good state.
- Uploads: uuid filenames, serve only basename, extension allowlist, 5-path-traversal encodings blocked.
- Do not import heavy graphs to read a small constant (e.g. read `COMMUNITY_ORDER` via `ast.literal_eval`), or you'll pull browser deps into a read-only UI.

## Never hand-write a timezone test expectation

The single most expensive mistake in this skill's test suite. Measured 2026-10-04:
26 checks, 1 failure — `Europe/London 09:07 -> 09:07 UTC`, got `08:07`.
London is **BST (+0100)** on 2026-10-05. The server was correct. My assertion
was wrong, and it was wrong *because I wrote it from memory instead of
computing it.*

```python
# WRONG — breaks the week BST starts, and on every DST boundary
for zone, expect in [("Europe/London", "09:07"), ("Asia/Kolkata", "03:37")]:
    ...

# RIGHT — the expectation comes from the same tz database the code uses
def expect_utc(zone, hhmm, day="2026-10-05"):
    local = datetime.fromisoformat(f"{day}T{hhmm}:00").replace(tzinfo=ZoneInfo(zone))
    return local.astimezone(timezone.utc).strftime("%H:%M")
```

A hand-written table is a claim about the world that expires on a DST
boundary. Compute it, and remember the failure is as likely to be the
*assertion* as the code — print `offset` before changing either.

**Cover both signs plus the awkward middle.** Four zones is not enough. A sign
flip is the bug that ships; test at least: negative half-day (`America/New_York`
−0400), positive half-hour (`Asia/Kolkata` +0530), positive with DST
(`Europe/London` +0100), and **beyond ±12** (`Pacific/Auckland` +1200,
`Australia/Sydney` +1100). A sign error can pass every in-range test.

## Applies to

Posting schedules, engagement ticks, cron entries, drip campaigns, any
recurring job whose *audience* is a human in a specific timezone. Same bug
shape as "email the digest at 8am" where the host is UTC — it is a 1:30am
delivery, and nothing anywhere reports an error.
