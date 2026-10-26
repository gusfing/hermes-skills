# Running a User-Supplied Social Posting Spec

When a user pastes a growth/posting playbook and says "follow this exactly",
the numbers in it are usually drafted for a mature account, not theirs. Build
it, run it, and keep the dialled-back parts visible.

## Build the spec as asked, then state the delta

Structure that worked: implement the spec's structure exactly, apply the safety
caps the platform actually enforces, and say plainly which numbers were changed
and why. Do not silently rewrite the spec — do not silently obey it either.

Spec: 8 posts/day, engage every 30 min, 2-3 DMs per loop, 24h loop.
Delivered: 8 posts/day, 4-6 comments per loop, **DMs disabled**, engagement
08:00-23:00.

Flagged at the time:
- 10 posts/day on a dormant account reads as bot behavior. Suggested 4 and
  scaling on week-one impressions.
- 2-3 DMs per 30-min loop is 40-50/day against a hard ~20/day cap. Left off in
  code as `MIN_DMS = 0` with a comment saying it turns on when a target list
  exists.
- The spec said the community posting path was broken. It was not. Verified and
  corrected rather than taken at face value.

The user accepted this and it worked. Silently capping looks like disobedience;
capping with the number named looks like judgment.

## One dial per risky dimension

Keep the spec's parameters as module-level constants so a volume change is a
one-line edit, not a code change:

```python
MIN_COMMENTS, MAX_COMMENTS = 4, 6
MIN_DMS, MAX_DMS = 0, 0        # ~20/day hard cap; enable with a target list
```

## A style spec should be a machine check, not a vibe

"Casual, no corporate language, no hashtags" is only enforced if something
fails. Turn the spec's style rules into assertions so a bad batch cannot ship:

- no `#` anywhere
- length ceiling (275 for X, 220 per the spec's "when possible")
- a banned-word list for corporate/AI tells: *delve, leverage, robust,
  seamless, furthermore, game-changer, unlock the power, in today's fast-paced*
- the hook must be detectable — require a hook marker and cap first-line length
- a `style` in the filename so coverage is checkable, and assert every declared
  style is represented

An assert-based script with no framework is enough, and it should exit non-zero
so a scheduled run cannot publish a batch that fails the user's own rules.

## Randomize the times the spec left open

The spec gave fixed hours for feed posts but windows for community posts. Honor
that distinction — fixed slots for the fixed ones, a random minute inside the
window for the rest. That was an explicit user request, and it is also the
difference between a schedule and a machine.

## State file so a missed window does not fire a burst

Each tick posts **at most one** due slot and records it. Without that, a
reboot at 14:00 posts six queued posts back to back. Track posted slots by
`(file, community)` per day.

## Verify the automation itself before trusting the timer

A live timer on an unverified code path silently burns an account. Before
enabling, run one post and one reply through the real script and confirm each
one on a feed. `systemd-analyze --user verify` the unit — a bad `OnCalendar` or
a `Requires=` cycle on the service it triggers will refuse to start, and
`*-*-* 08..23/1:00/30` is the form that works for every 30 min in a range.
