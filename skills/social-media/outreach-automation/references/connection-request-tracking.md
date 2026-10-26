# Connection-request send tracking: when "SENT" writes nothing

Measured 2026-10-01. Two faults stacked, and the second one made the first
invisible. Both were silent — no error, no exception, a log full of `SENT`.

## Fault 1 — no timer

`li_connect.py` had been run by hand 33 times and reported as working. It had
never had a `.service`/`.timer`. The user noticed a day later
(*"you didnt send connection request today you lied also"*).

Fix is a `Type=oneshot` service plus a timer whose `per_run x ticks` equals
`per_day` in config. A timer with no matching row in
`systemctl --user list-timers` is not a schedule.

## Fault 2 — the send was never recorded

The send path was:

```python
if ok:
    sent += 1
    if p.get("id"):
        P.mark(p["id"], "sent", note_sent=note)
    log(f"  SENT ({reason})  total={sent}")
```

The pool is `/tmp/li_pool.json`, built by the scraper. **Scraped records have no
`id` key at all.** So the `if` never fired, `P.mark` was never called, and the
row was never written.

Consequences, all invisible from the send log:

- `sqlite3 ... where date(touched_at)=today` returned **0** after three
  confirmed `SENT` lines.
- The 7-day cooldown had nothing to protect, so those people were immediately
  eligible for re-invite.
- The DB row count (34) looked like the pool size, which is how I came to
  report "1 person left" when 171 were eligible.

### The fix: upsert by URL

URL is the stable key, and the cooldown query already uses it.

```python
def mark_url(url, state, name=None, note_sent=None, skip_reason=None, fit=None):
    """Same as mark() but keyed on the profile URL.

    Needed because the live pool is a scraped JSON file — records with no
    `id`. Without this, an invite that genuinely went out left no row, so the
    cooldown did not apply and the person could be re-invited immediately.
    """
    conn = init()
    try:
        cur = conn.execute(
            """UPDATE people
               SET state=?, note_sent=COALESCE(?, note_sent), skip_reason=?,
                   icp_fit=COALESCE(?, icp_fit), touched_at=?
               WHERE url=?""",
            (state, note_sent, skip_reason, fit, now(), url),
        )
        if cur.rowcount == 0:
            conn.execute(
                """INSERT INTO people (url, name, channel, state, note_sent,
                                      skip_reason, icp_fit, touched_at, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (url, name, "linkedin", state, note_sent, skip_reason,
                 fit, now(), now()),
            )
        conn.commit()
    finally:
        conn.close()
```

Call it without an `id` guard, and wrap it so a write failure is loud rather
than silent — the invite **was** sent, so losing the row must not be quiet:

```python
try:
    if p.get("id"):
        P.mark(p["id"], "sent", note_sent=note)
    else:
        P.mark_url(p["url"], "sent", name=name, note_sent=note)
except Exception as e:
    log(f"  DB WRITE FAILED for {name}: {e} — invite WAS sent, not "
        f"tracked, cooldown will not apply")
```

### Backfill after the fix

Sends made while the write was broken are real sends with no row. Reconstruct
them from the send log's `SENT` lines, then let cooldown apply:

```python
for n in ["Hitesh Bhandari", "Tanmay Chauhan", "Nilesh Tiwari"]:
    hit = [p for p in pool if p.get("name") == n]
    if hit: P.mark_url(hit[0]["url"], "sent", name=n)
```

## Verify with a control, not the log

The log said `SENT`; the DB said nothing. Only the DB is the control:

```bash
sqlite3 outreach.db \
 "select name, state, touched_at from people
  where date(datetime(touched_at,'+5 hours','utc'))='2026-10-01' order by touched_at"
```

A send log is a claim by the process that did the work. The state table is an
independent artifact. When they disagree, the table is the one to believe —
and a run is not finished until the row exists, because the row is what the
cooldown, the dashboard and the next run will all read.

## Two general rules this exposed

1. **A guard on a key that is usually absent is a silent no-op.** `if p.get("id")`
   reads as defensive and is in practice dead code. Prefer a path that always
   records over one that records conditionally.
2. **The inventory and the log are different files.** `people` is a write-back
   table, not a queue. Capacity numbers must come from the worklist the sender
   actually iterates.
