# Tick ledger and observability for unattended loops

Born 2026-09-30 from *"i can know when you are engaging in x and when not"*.

## Why a JSONL ledger rather than a log file

A systemd text log records what the code chose to print. A ledger records what
happened, at every exit, including the paths where nothing was printed because
the run never got far enough. One JSON object per line so a process killed
mid-write still leaves a parseable prefix, and so `tail`-style reads never
require loading the whole file.

```python
IST = timezone(timedelta(hours=5, minutes=30))   # named for the audience

def record(channel, outcome, detail="", counts=None, trigger="timer", started=None):
    started_ts = started if started is not None else time.time()
    row = {
        "started": started_ts,
        "at":    time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(started_ts)),
        "at_ist": datetime.fromtimestamp(started_ts, IST).strftime("%Y-%m-%dT%H:%M:%S"),
        "channel": channel, "trigger": trigger, "outcome": outcome,
        "detail": str(detail)[:200], "counts": counts or {},
    }
    try:
        with LEDGER.open("a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass        # never let bookkeeping break an outreach run
```

**Do not use `time.localtime()` for the local column.** On a UTC host it is UTC,
and the column silently duplicates `at` — the one number the user will trust.
`datetime.fromtimestamp(ts, IST)` is the only correct form.

`recent(hours, channel)` filters on `started` and skips `JSONDecodeError`
lines; size-based rotation (`os.replace` to `.jsonl.1`) beats a daily path,
which would need a separate file per date.

## The placement bug that makes the ledger lie

Every `record()` call sat **inside** the function that runs under the browser
lock. Result: the 18:00 tick that gave up after 1500s waiting for the lock
left zero rows. The lock is acquired before the first call site, so the one
failure mode that looks most like "nothing is scheduled" was the one failure
mode with no record.

**Record the attempt where the resource is contended, not in each caller.**

```python
    if not got:
        print(f"[lock] gave up after {timeout}s waiting for the browser")
        f.close()
        try:
            import tick_ledger
            tick_ledger.record("x" if name == "x_loop" else "linkedin",
                               "halted",
                               f"browser lock held by another job ({timeout}s wait)",
                               trigger=name)
        except Exception:
            pass
        sys.exit(3)
```

Note the real contract discovered by reading `cdp_lock.py`, not by assuming it:
it **prints and calls `sys.exit(3)`** — it does not raise. A first attempt
wrote `except LockBusy:` against an exception class that does not exist in the
module and would have crashed on import.

## Outcome vocabulary

`posted` / `engaged` (did work) vs `skipped` (ran, nothing due — a success, not
a fault) vs `halted` (blocked: lock, captcha, 0 cards) vs `error` (a real
fault). The `skipped` row is the one users misread as a failure, so it needs
its own glyph and its own `detail` explaining *why* nothing was due.

## Read counts back, do not report the request

```python
def x_recent_counts(asked):
    n_reply = n_follow = 0
    cutoff = time.time() - 600
    fp = HERE / "x_engage_log.json"          # measured path, not a glob guess
    rows = json.loads(fp.read_text()) if fp.exists() else []
    for r in rows if isinstance(rows, list) else []:
        ts = r.get("t")                       # measured key: epoch "t", not "at"
        if not isinstance(ts, (int, float)) or ts < cutoff:
            continue
        if r.get("type") == "follow":
            n_follow += 1
        else:
            n_reply += 1
    return {"replies": n_reply, "follows": n_follow, "asked": asked}
```

A first draft globbed `logs/x_engage*.json` — the real file is
`x_engage_log.json` in the project root. Guessing a log path is the same class
of error as guessing a selector.

## Serving it over HTTP without a second implementation

The user asked for a **URL**. Do not rewrite the numbers for the web view —
reuse the CLI's own renderers and capture stdout:

```python
def render(days=1):
    buf = io.StringIO()
    with redirect_stdout(buf):
        dashboard.show(days)
    return buf.getvalue()
```

`ThreadingHTTPServer`, bind **127.0.0.1**, nginx is the public edge, systemd
unit with `Restart=always` + `ProtectSystem=strict` +
`ReadWritePaths=<project>`. Reuse existing nginx conventions; check
`ss -ltn` for a free port first (8787 was taken by another service, so the
dashboard went to 8791). `/healthz` returning `ok` and a
`Host: dash.kawaki.co.in` request through nginx both prove routing before any
DNS record exists.

**Flag missing auth explicitly when the listener goes public.** The page
exposes prospect names and pool contents; say so rather than shipping it
silently.

## The general rule

For any unattended system, the question "was it working, and when?" must be
answerable **from a data source the run itself wrote**, at every exit path.
Print-based logging answers "what did the happy path do", which is the one
case the user is least worried about.
