# A run that never happened looks exactly like a run that did nothing

The user asked for a dashboard "so I know when you are engaging and when not".
Counts could not answer it, and the reason generalises well beyond social
automation: **the absence of a log is not the absence of work, and it is not
evidence of a failure either.**

## The two failures that look identical

| what happened | counts-only view |
|---|---|
| timer fired, min-gap floor said wait | no change |
| timer never fired / died on a lock | no change |
| script exists but nothing invokes it | no change |

All three read as "nothing happened". Two of them are bugs. Reporting on
counts means the user has to *ask* which one it is — and they will, and the
question is really a complaint that the automation is opaque.

## The fix: a per-run ledger

One JSON object per line, appended at **every** exit path:

```json
{"started": 1790792805.8, "at": "...", "at_ist": "...",
 "channel": "x", "trigger": "timer", "outcome": "posted",
 "detail": "community post + engage", "counts": {"replies": 5}}
```

- JSON lines, not one JSON array: a run killed mid-write still leaves a
  readable prefix, and `tail` never needs to parse a whole file.
- `outcome` vocabulary must separate **worked** (`posted`, `engaged`) from
  **correctly did nothing** (`skipped` — floor not met, slot not due) from
  **failed** (`halted`, `error`). Collapsing these is what makes a dashboard
  useless.
- **Tolerate a truncated last line** in the reader; a killed run is normal.

## Record the runs that never got in

This is the part that is easy to get wrong. If every `record()` call sits
*inside* the critical section, then a run that never acquired the lock leaves
**no record at all** — and that is exactly the invisible case. Measured: a tick
waited 1500s for a shared resource, gave up, exited non-zero, and nothing
anywhere recorded that it had tried.

Put the failure record **at the point the resource is refused**, inside the
lock/context-manager itself, so every caller benefits and none can forget.

## Log what happened, not what you asked for

Read the counts back out of the run's own log when writing the ledger row. A
tick asked for 5 replies and landing 2 must not record 5 — a ledger built from
the requested arguments is a ledger of intentions.

## Prove the ledger records before trusting it

A ledger that has never held a real row looks identical to one that is working.
Force each branch once and read the row back:

- success path (real run)
- lock-refused path (hold the lock in a second process, use a short timeout)
- and delete the synthetic rows afterwards, or the next reader mistakes a test
  for history.

Rendered output that earned its keep:

```
● 23:56 IST  x         posted    community post + engage      replies=5 (9m ago)
● 00:05 IST  linkedin  engaged   feed had 9 cards             likes=2 (0m ago)
● 00:17 IST  linkedin  engaged   feed had 9 cards             likes=1 comments=2
```

Times in the **audience's** zone, converted from the stored epoch — not from
the host's local clock, which on a UTC box silently duplicates the UTC column.

## "It's running" needs a scheduled unit, not a working script

The other half of the question. A script that works when invoked by hand is
**manual**, and saying "it's running" about it is an overclaim the user is
entitled to reject. Name the unit before claiming anything is active:

```bash
systemctl --user list-timers <name>.timer --no-pager
ls ~/.config/systemd/user/ | grep <name>     # does a .service/.timer exist at all
```

No `.service`/`.timer` pair on disk means nothing has ever invoked it
unattended. When a component is *supposed* to be scheduled, wiring the timer
is part of building it — not a follow-up. This one shipped a "33 sent" report
for a job that had only ever been run by hand.
