---
name: evidence-before-claiming
description: Demand named evidence before claiming fixed.
---

# Evidence Before Claiming

A claim is a promise that someone will not have to re-check. Most of my
overclaiming came from one habit: reporting a conclusion when I had only run a
probe. This skill is the checklist I skipped.

## The three tiers — always know which one you are in

- **Measured** — I ran a command and saw output. Quote it.
- **Inferred** — output supports it, but something else could also produce that
  output. Say "consistent with", not "is".
- **Guessed** — no output. Say "I think" and state the test that would settle it.

Saying "Found it" is a measured-tier claim. Only use it with a command + its
output in the same breath. If you cannot paste the output, you are at best
inferred.

## Probe validity comes before probe conclusion

My worst errors were not bad hypotheses — they were broken probes read as
findings, then acted on:

- Passed a full `redis://host:6379` URL as ioredis's `host` option. Got a real
  `getaddrinfo ENOTFOUND`. Briefly treated that as a genuine failure. The probe
  was wrong, not redis.
- Queried `where amount=600`. Got 0 rows. Concluded "prices were never written."
  Amounts are in paise — it was `60000`. Reported a false failure to the user.
- Read "zero Redis sockets" as proof Redis wasn't the blocker, when the
  handle-dump was taken during a different phase than the failure.

**Rule: when a probe result contradicts what I believed, suspect the probe
first.** Check that the probe ran against the right target, in the right phase,
with the right units, before I explain the result. A surprising result is
evidence *about the probe* until proven otherwise.

## Banned unless the check ran in this same task

- "fixed" / "works" / "done" / "deployed" / "live"
- "verified" — requires a named check and its actual output
- "no secrets committed" — requires a `git grep` at HEAD, not a glance at
  `git status`
- "created successfully" — when a later step in the same command failed, the
  earlier step's success is not the task's success
- "up to date" / "no errors" — paste the grep count

## Report partial success honestly

`BUILD_EXIT=0` is one fact, not a deployment. If only part of a task is done,
say which part, name the rest, and do not round up to a green summary.

## Child claims are not facts

A subagent saying "installed 12 skills" is a self-report. Count the files, read
the paths, re-run the check. Do not relay a child's success claim upward.

## Before I write the final line

1. Did the check I am about to cite actually run? Paste its output.
2. Is my claim measured, inferred, or guessed — and does my wording match?
3. If a probe surprised me, did I validate the probe before believing it?
4. Am I rounding a partial result up to a complete one?

If any answer is no, fix the wording before sending, not after being corrected.

## Why this exists

On the Bazzaro migration I asserted a root cause four times before instrumenting
anything, declared a fake redis instance the culprit, and reported prices as
missing when my query used the wrong unit. The user noticed. The cost was
roughly an hour of their time and a lot of trust spent on wrong answers.

The habit to build: instrument first, conclude second, and never let the
confidence of my sentence exceed the strength of my evidence.
