# Pipeline audit — 2026-10-03

Audit of `/home/opc/kawaki-outreach/` (X + LinkedIn automation) after the
posting-only directive. 51 findings; this records the ones that change what you
do next. Line numbers as of 2026-10-03.

All outreach timers were **stopped and disabled** at audit time. Findings below
are latent, not active.

## CRITICAL — X

### 1. `x_post.py:287-299` — `confirm()` returns `null` on every call

The status-id extraction is an **already-invoked** IIFE:

```python
(h => { ... href.indexOf('/' + h + '/status/') ... })()   # <- invoked
```

Playwright's injected `evaluate` passes an argument only for a *bare function
expression*. The trailing `()` makes `isFunction` false, so `HANDLE` is dropped,
`h` is `undefined`, and `indexOf('/undefined/status/')` never matches.

Evidence: `x_state.json` has `"status": null` on **all 6** recorded posts.

The regex itself is correct; the argument plumbing is the bug. A comment claims
this was fixed on 2026-10-01. It was not.

Corollary for any CDP wrapper: pass the **call** (`location.href`), not the arrow
function. An arrow function serializes to `{}`, which looks exactly like a dead
target — that misdiagnosis cost a full debugging cycle.

### 2. `x_schedule.py:69-91` + `x_loop.py:106` — the plan is redrawn every tick

`build_plan()` calls `rnd.randint(0,59)` per slot with no seed, and **every
caller builds a fresh plan**. Measured: two consecutive `build_plan(day=D)` calls
disagreed on every slot minute; across 40 calls one nominal hour landed on 11-17
distinct minutes; **29 of 29 posts in a simulated day fired at a time other than
their planned time.**

Slot *hours* are fixed, so the gap floor is not violated — the schedule simply
does not exist. `x_plan.json` is written by the manual `--plan` flag and **no
scheduler ever reads it**.

Fix: build once per day, persist, have every reader load the same file.

### 3. IST/UTC day mismatch silently kills the last 3 hours

`build_plan()` plans for `ist_day()` (IST, correct). Every "is it due" comparison
uses naive `datetime.now()` (**UTC**), and `x_state["day"]` is the **UTC** date.

From 18:30 UTC (00:00 IST) to 21:30 UTC the plan targets *tomorrow* IST while
state tracks *today* UTC. Measured at 20:00 UTC: plan built for 2026-10-04 has
**0 slots due**; the tick prints `[plan] nothing due` and returns 0. Every time.
`x-daily.timer` covers exactly that range.

Day rollover also happens at 00:00 UTC = 05:30 IST, mid-window.

Fix: derive both the due-check and the state day from `ist_day()`. See
`timezone-aware-scheduling`.

## HIGH — X

### 4. `x_loop.py:91-100` — research output never feeds posting

`angles[]` is written by `x_research.py` and displayed by `dashboard.py:301`.
**No consumer.** Every post text comes from static `x_pool/*.txt`.

The "research gates writing" docstring is false: the gate refuses to post when
research is *stale*, while the posts themselves are pre-written and unsourced. A
gate on the freshness of an input nothing reads is decoration.

### 5. `x_schedule.py:97-101` — exhaustion silently reuses

```python
if len(avail) < len(slots):
    avail = pool      # exhausted -> allow reuse rather than skipping a slot
```

Live: pool 23, used 18, avail 6, slots 10 → branch fires, **8 of 10 assigned
files already used.** Same-day duplicates are impossible (0/300 plans), so only
the cross-day guarantee fails.

### 6. `x_daily.py:202` + `x_schedule.py:176` — two paths post text-only

Only `x_daily.py:111` (the shared `post_and_confirm` path used by `x_loop`)
passes an image. All 23 pool files have a matching `x_media/<stem>.png`, so the
assets exist and these paths simply ignore them. The comment at
`x_daily.py:105-108` claims every post carries an image.

### 7. `x_post.py:66` `pick()` — dead code

The three-level fallback ending in bare `pool` exists as described but has **zero
callers** (`grep '\bpick('` finds only the def). The live reuse is finding 5.
Dead code that reads like the bug sends the next audit to the wrong line.

### 8. `x_daily_tick.py` — no callers

Not in systemd, not in cron. It also selects a due slot then shells out to
`x_daily.py`, which picks independently: ticker chose `20_confession.txt`, child
posted `01_confession.txt`.

### MEDIUM — X

- `x_post.py:324-334` — `x_used.json` writes `Path(a.file).stem`
  (`01_confession`) while every consumer compares `p.name` (`01_confession.txt`).
  Stem entries can never match; the file only grows.
- `x_daily.py:63,66,69` — `get_last_post_age()` reads the **first** `<article>`
  on the profile, which includes our own replies and reposts.
- `x_post.py:246` + `x_daily.py:118-120` — a failed community post records
  nothing and retries every tick, because slot times and the community choice
  are both re-randomized.
- `x_loop.py:92-99` — research-failure early returns exit **before** any
  `tick_ledger.record()`. A tick that researched and posted nothing is
  indistinguishable from a tick that never ran.
- `x_engage.py:73-155` — `--comments N` is a no-op: `done` is never appended,
  and line 153 breaks after one candidate. Ledger shows
  `{"replies":1,"asked":5}`.
- `x_post.py:353`, `x_engage.py:168`, `x_schedule.py:166` — unguarded `[0]` on
  the tab list; `IndexError` when no x.com tab exists.
- Dead config: `x_schedule.py:21,20` imports `config` unused;
  `ENGAGE_MIN/ENGAGE_EVERY/ENGAGE_COMMENTS/ENGAGE_DMS` have no readers;
  `x_post.py:34-48` `COMMUNITIES` (13 ids) has no reader.
- `cdp.py:100-108` — `type_text`'s JS `const sel` shadows the injected selector
  parameter. Works today, live footgun.

## CRITICAL — LinkedIn

### 9. `li_engage.py` is truncated to 141 lines — no `main()`, no `__main__`

Self-inflicted during the comment removal. `wc -l` = 141, `grep '^def \|^if
__name__'` shows 8 defs and **no entry point**. Running the timer's exact command
gives `exit=0`, no output, no work.

`x_selfcheck.py` PASSed throughout — "no comment code" is trivially true of a
file with no code.

### 10. `li_connect.py:376-382` — pool head-slice starves every tick

`people[start:start+limit]` slices from the head of the pool. All 42 pool-head
entries are `state='sent'` or in the 7-day cooldown. Simulated:

```
start=0 limit=5 -> pool head 5 people, 0 sendable
```

No ledger row, no error, no `--start-index` in the unit. **Starvation is
permanent, not per-tick.** With timers re-enabled, outreach would look like it
was running and never run.

### 11. `li_connect.py:357-364` — the 30/day cap has no reader

`cap` only trims the current batch and breaks `if sent >= cap` (this run's count
against a daily limit). `runner.sent_today()` is **never called in this file**
(grep count 0). Compounding: the unit has **7** `OnCalendar` ticks x `--limit 5`
= 35/day against a 30 cap, while its own comment says "6 ticks".

### HIGH — LinkedIn

- `li_connect.py` (whole file) — no `cdp_lock`, no `tick_ledger.record`. It is
  the only sender, and `x_loop` takes the lock while `li_connect` does not: two
  CDP clients, the exact handshake stall `cdp_lock.py` exists to prevent. Its
  header comment says "Nothing here sends" — false.
- `li_connect.py:357` — `json.load(open(POOL))` unguarded. Pool deleted →
  traceback, tick dies, no ledger row.
- `li_reply.py:97-137` — **zero DB writes.** DMs are invisible to the dashboard
  and there is no cooldown, so the same person can be DMed repeatedly.
- `config.py:29,30` — `per_run: 5` and `min_seconds_between: 300` are **dead**.
  Real pacing is `li_connect.py:47` = 70-150s, more than twice as fast as the
  declared config. Raising pacing in config does nothing.
- `config.py:91` vs the unit — `WINDOW` is 09:00-17:00 but the timer runs
  09:15-03:15 IST, and `in_window()` is never called anyway.
- `pipeline.py:35` vs `:150,163` — schema comment says
  `queued|skipped|contacted|replied|blocked`, but `runner.py:129` writes
  `'planned'` and `li_connect.py:446` writes `'sent'`. **Neither is in the
  documented set**, so `next_batch(state="queued")` returns 0 rows (verified).
- `pipeline.py:193-200` — `messages` table has 0 rows; `save_message` is never
  called, so drafted notes are lost.
- `runner.py:110` — dead branch refusing to draft because `OFFER` is empty.
  `config.OFFER` is set at `config.py:13`.
- `li_connect.py:440` vs `:446` — the comment describing the missing-`id` bug
  is accurate history; the `mark_url()` fallback is the fix, and it works
  (42 rows `state='sent'`). This suspicion is **refuted**.

## Confirmed capabilities

- **LinkedIn has no posting path at all.** Zero code. `li_connect` = invites,
  `li_reply` = DMs, `li_engage` = likes (and dead). X has a full posting
  pipeline; LinkedIn has none. `x_selfcheck` enforces "posting only, no
  comments" — for a post path that does not exist.
- **7-day cooldown is the one guard that works.** `runner.in_cooldown()` reads
  `cooldown_days`, applied at `li_connect.py:380`. Verified live. Caveat: a
  missing `touched_at` returns False, so a DB-write failure silently re-enables
  re-invite.
- **`card_url()` returns `""` unconditionally** (`li_engage.py:85`). 175 log
  rows, 0 with a URL. Confirms the dashboard cannot show a LinkedIn permalink —
  by design, not bug.

## Dashboard lies

- `dashboard.py:71-73` — `sent_today` uses SQLite `date('now')` = UTC, and
  counts **rows, not sends**: a person marked `sent` twice counts once.
- `dashboard.py:321` — cap divisor is raw `LIMITS.per_day`, not
  `config.cap_for`. Hardcoded fallback `30` at `:319`.
- `dashboard.py:326` — `li_likes_cap = 3 * 30 = 90` is invented; no likes/day
  limit exists anywhere in `config.py`.
- `dashboard.py:324` — quota text hardcodes "October" and prints a hardcoded
  "0 left" instead of reading `read_note_allowance()`.

## Not confirmed / wrong

- `x_post.py:66` `pick()` — real code, **zero callers**. Not the live bug.
- `x_daily.py` timestamp regex — **correct**. Verified against the exact runtime
  string. An earlier probe suggesting corruption was a JS-escaping error.
- `x_post.confirm()` regex — **correct** in isolation. The bug is arg-passing.
- `x_pool` quarantine file — `.bak` is not matched by `glob("*.txt")`, correctly
  excluded.

## `/tmp` pool expiry

`/usr/lib/tmpfiles.d/tmp.conf:11` carries `q /tmp 1777 root root 10d`. The pool
`/tmp/li_pool.json` (dated 2026-09-29) is deleted at **10 days**, not at reboot,
and no script in the repo writes it. A deleted pool means
`json.load(open(POOL))` raises, the tick dies, and no ledger row is written.
Campaign state does not belong in `/tmp`.