---
name: cold-outreach-pipeline
description: Build outreach queues that draft messages and pace sends.
---

# Outreach pipeline that plans but never auto-sends

Cold outreach fails for two reasons that a script cannot fix: an unclear offer,
and a message that reads as generated. What a script *can* do is keep the
queue honest, pace the volume, and refuse to send anything until a human
approves it.

## Build in this order

1. **Queue with state** — SQLite, one row per person, `state` in
   `queued|planned|contacted|replied|blocked|skipped`. Partial progress must
   survive a crash, so a single JSON blob is wrong.
2. **Counter-enforced caps** — count today's actions from the `runs` table, not
   from memory. A cap you remember is not a cap.
3. **Per-person cooldown** — `touched_at` compared against
   `cooldown_days`. Never contact the same person twice in a week.
4. **Time window enforced in code** — 9-5 in `config`, checked at plan time.
   A cron schedule is not a substitute; anything else can fire the runner.
5. **Message templates that return `None` when the offer is unset** — an
   empty draft is honest. A draft built on an empty `OFFER` produces
   "we leverage synergistic solutions" spam, and one such message to a real
   person costs a connection that cannot be recovered.
6. **Report to a file** — a human reads the plan and executes it. Never have
   the script press Send.

## Injection seam for the clock

`in_window(now=None)` silently falling back to `datetime.now()` is a real
bug source: the timestamp written into the report and the window decision came
from two different clocks, so a faked 10:00 still reported "outside window".
Thread `now` through every function that decides or timestamps. Test the
window by injecting a clock, never by waiting.

## Tone rules that matter for a first message

- Open with the recipient's name and one specific true thing about them.
- The WhatsApp first touch asks **one small question** and makes refusal easy.
  A pitch in message one ends the conversation.
- Never claim a shared interest or mutual connection you have not verified.
- Under 300 chars for a LinkedIn note; over that it is truncated, not read.
- Have several variants and select on something real (their sector), not at
  random — a random variant reads as a mail merge.

## Report the quality of the list, not just its size

Keyword search returns whoever matches the keyword. On one run, `saas founder
delhi` returned 14 profiles of which 11 were tissue-paper manufacturers, car
rentals, and gym brands. State the off-ICP rate explicitly. A long list of the
wrong people is worse than a short list, because sending to it burns the
account.
