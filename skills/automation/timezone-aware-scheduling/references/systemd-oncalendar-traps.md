# systemd `OnCalendar` traps

Both traps below are **silent**. They parse, `systemd-analyze --user verify`
passes, `systemctl --user status` shows `active`, and the timer does not do what
the line reads like it says. Measured on systemd 252.

## Trap 1 — a comma hour list is not a range

```
OnCalendar=Mon..Sat *-*-* 03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18:00/30
```

Looks like 16 hours at 30-min intervals. Actually fires **once a day at 18:00**.

Correct range syntax is `..`:

```
OnCalendar=Mon..Sat *-*-* 03..18:00/30
```

`03..18:00/30` = 03:00, 03:30 ... 18:00.

Also rejected / not equivalent, in case they look tempting:

| spec | fires |
|---|---|
| `*-*-* 03:00..18:30/30` | never |
| `*-*-* 03:00/1h` | never |
| `*-*-* 03:00/1:30` | 03:00:30 — parses as seconds-after-the-hour, then repeats hourly |
| `Mon..Sat *-*-* 03:00,30 09:00,30` | never — mixing lists and a second time group in one spec is not allowed |

## Trap 2 — a `:MM/repeat` spec yields `Trigger: n/a`

```
OnCalendar=Mon..Sat *-*-* 03:15/30     # wanted :15 and :45
```

Parses without error; `systemctl --user show <u>.timer -p Trigger` returns
**`n/a`** and the timer never fires. Check `Trigger` explicitly after any
offset spec — `ActiveState=active` alone does not prove it is armed.

There is no working `:MM/repeat` offset. Use a distinct hour range instead and
accept the drift, or gate concurrency in the job itself with a lock (which is
usually the real requirement anyway).

## Verify with `systemd-analyze calendar`, read `Normalized form`

```bash
systemd-analyze calendar "Mon..Sat *-*-* 03..18:00/30"
```

```
Original form: Mon..Sat *-*-* 03..18:00/30
Normalized form: Mon..Sat *-*-* 03..18:00/30:00
    Next elapse: Wed 2026-09-30 18:00:00 GMT
```

**Read `Normalized form`, not the fire count.** The tool prints only the *next*
elapse, so counting `Next elapse:` lines — with or without `--iterations` —
gives 1 even for a correct every-30-min spec. That produced a confident,
completely wrong "it only fires once a day" conclusion mid-debug. The
`Normalized form` line is the ground truth on how the spec was understood.

## Trap 3 — minute ranges do not exist

`OnCalendar` ranges are **hour** ranges. Every attempt to express a window whose
edges are not on the hour is rejected outright:

| spec | result |
|---|---|
| `Mon..Sat *-*-* 03:30..21:30:00/30` | `Failed to parse` |
| `Mon..Sat *-*-* 03:30..21:30` | `Failed to parse` |
| `Mon..Sat *-*-* 03:00..21:30/30` | `Failed to parse` |
| `Mon..Sat *-*-* 03..21:30/30` | `Failed to parse` |
| `Mon..Sat *-*-* 03:30/1h30m` | `Failed to parse` |
| `Mon..Sat *-*-* 04:00,30 05:00,30 06:00,30 …` (one long line) | `Failed to parse` |

## Trap 4 — one time-of-day per line, so use the list idiom

**At most one time-of-day per `OnCalendar=` line.** A single line cannot hold a
comma-separated list of times *plus* a repeat suffix. Multiple `OnCalendar=`
lines are not a bug — they are the documented **list** idiom, and they are the
only way to express a window with off-hour edges.

```ini
[Timer]
OnCalendar=                          # bare line RESETS the list
OnCalendar=Mon..Sat *-*-* 03:30      # window opens   (09:00 IST)
OnCalendar=Mon..Sat *-*-* 04..21:00/30   # every 30 min
OnCalendar=Mon..Sat *-*-* 21:30      # window closes  (03:00 IST)
```

This verifies clean and each line normalises independently. Use it whenever the
audience window is not hour-aligned — note the example above spans 09:00→03:00
*local* while being contiguous in UTC, which is the usual reason the edges land
off-hour.

To confirm a list actually took, read the unit back and normalise every line —
`scripts/check_timer_window.py` does exactly that. A bare reset line with no
following entries means an empty schedule, so check the list is non-empty
rather than trusting `ActiveState=active`.

## Also fails, and is a useful reminder

- Mixing `08` and `08:30` in one spec → `Bad unit file`. Consistent form.
- A repeat suffix (`/30`) combined with an hour *list* (Trap 1) is the single
  most likely way to end up with a timer that looks armed and runs hourly at
  most.
- A second time-of-day appended to an existing line without a reset
  (`03:00 04:00` on one line) → `Failed to parse`. Use separate lines.

## Conversion: do it in Python

```bash
date -u -d '+5:30' "$TS"    # returns the input unchanged, no error
```

Use `strptime` + `replace(tzinfo=utc)` + `astimezone(IST)` instead. `date -u`
cannot add an offset. See the parent SKILL.md.
