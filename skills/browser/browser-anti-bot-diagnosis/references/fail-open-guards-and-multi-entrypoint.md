# Fail-open guards and multi-entrypoint drift

Findings from a live outreach run (2026-09-29) in which 30 real connection
requests were sent to real people, and a protection that had never once been
active. Both defects were **silent** — nothing raised, nothing logged, every
report looked healthy.

## 1. A missing guard key fails OPEN, not closed

```python
def in_cooldown(person, channel):
    cd = config.LIMITS.get(channel, {}).get("cooldown_days", 0)
    if not cd:
        return False          # absent key => "no cooldown", quietly
    ...
```

`cooldown_days` had been configured for one channel and omitted for another.
The lookup returned `0`, the `if` returned `False`, and the 7-day per-person
cooldown was inert for that channel for the life of the project. The daily cap
in the same config dict *did* work, which made the system look healthy in every
dashboard and report.

The tell: the guard and a *different* guard lived in the same struct, and only
one was configured. A partial struct is indistinguishable from a full one at
runtime.

### Defensive shape

```python
# Every guard key must exist for every channel. Startup, not first contact.
for ch, lim in config.LIMITS.items():
    assert lim.get("cooldown_days"), f"{ch}: no cooldown_days, in_cooldown() is a no-op"

# Then exercise BOTH branches, so a correct config with an inverted comparison
# cannot pass a presence-only check.
assert cooldown({"touched_at": now}, ch) is True          # just contacted -> blocked
assert cooldown({"touched_at": now - 30d}, ch) is False  # stale -> allowed
assert cooldown({}, ch) is False                          # never contacted -> allowed
```

Three lines, and they convert a silent no-op into a loud startup failure.

**Generalisation.** Any lookup that decides *safety* rather than *behaviour*
(`if not policy: return permissive_default`) should invert to fail-closed:

```python
cd = config.LIMITS.get(channel, {}).get("cooldown_days")
if cd is None:
    raise ConfigError(f"{channel} has no cooldown_days; refusing to send")
```

Raise loudly on the ambiguous state. The cost of a false "I thought I had a
guard" is unbounded; the cost of a startup error is one message.

## 2. A second entry point bypasses every DB rule without any error

The cooldown was correctly present in config. It still did not apply, because
the **sending** script read its prospect list from a JSON file and never opened
the database. All state-based rules — cooldown, daily caps, `state`
transitions — live in the DB and are invisible to a script carrying its own
list.

```
planner (runner.py)  -> queries the DB, honours cooldown, writes reports
sender  (li_connect.py) -> loaded /tmp/pool.json, never touched the DB
```

Nothing about the sender looked wrong. It logged cleanly and sent 30 invites to
people invited earlier the same day.

### Rules

- **One source of truth for the worklist.** If a file is needed, treat it as a
  cache and re-validate every record against the DB immediately before acting.
- **Filter the batch against the DB in the same process that sends**, not at
  planning time in a different one.
- When adding a second entry point, grep for who opens the DB. Duplicated
  selection logic is where the two copies diverge.
- A verification that matters: re-run the sender in dry-run over an
  already-contacted range. It must report `N skipped: in cooldown`, not a fresh
  batch. If it re-plans, the guard is not wired.

## 3. Track what was actually sent, or the guard has nothing to protect

The same run recorded 33 sends, then found the DB had **zero** rows marked sent
— the sender worked from JSON and only called `mark()` for records that
happened to carry a DB id.

A cooldown is only as good as the `touched_at` timestamps it reads. Writes that
silently skip rows leave the guard correct in code and useless in practice.

After any run, assert the recorded count matches the dispatch count:

```python
assert db_sent_count == dispatched_count, "guard has no data to work with"
```

## 4. "Plans but never sends" needs an explicit escape hatch

The default — planning script separate from sending script, sending off unless
an explicit flag is passed — is right. Encoding it as an *absolute* produces one
of two failures: the agent sends when it should not, or it refuses work the
user deliberately authorised.

What held up under real use:

- Sending in a **separate script** from planning, off by default, armed by a flag.
- Dry-run first, then **one** real send verified end to end, then the batch.
- Once the user authorises a run, it is not re-litigated per recipient.
- Recipients still screened before each send: right profile, right control, and
  (where a note is required) the text confirmed to be in the correct field.

Note the last one: a selector that matched the *wrong* textarea would have sent
a direct message to a stranger. "Verify the field before sending" is not
belt-and-braces when two same-page textareas are both plausible targets.
