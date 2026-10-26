# CDP client contention: why `connect_over_cdp` "breaks" when it doesn't

Measured 2026-09-30 on an Oracle Linux ARM VPS, Chrome 9222, persistent profile.
Corrects an earlier, wrong conclusion in this repo that Playwright was simply
broken on this box.

## The data

| condition | transport | attach time |
|---|---|---|
| a second CDP client already attached | Playwright `connect_over_cdp` | **180 s timeout** |
| idle | Playwright `connect_over_cdp` | **1.2 – 2.0 s** |
| idle | raw websocket to the page target | 0.1 s |

Chrome at 0.2 GB RSS, ~0% CPU, on an idle desktop, 15 open targets.

**Playwright did not break.** It contends for the *browser-level* websocket.
Two clients on one Chrome stall each other in that handshake and the loser times
out with `TimeoutError: BrowserType.connect_over_cdp`. Raw CDP opens a
page-target socket directly and never queues on the browser socket, so it is
effectively immune.

## The rule

**Mutual exclusion, not a transport ban.** Any two jobs that drive the same
Chrome must take a lock file for their whole run.

- Lock at the *coarse* level — one job holds it across all its phases (research
  + post + engage), not per-attach. Per-attach locking still interleaves two
  jobs inside one tick.
- Two timers on one browser must be **offset**, not simultaneous. A 15-minute
  offset is what kept a LinkedIn and an X timer from racing; `Requires=` between
  them only serialises ordering and is not mutual exclusion.
- A killed run leaves a stale lock that silently swallows the next run's stdout
  while exiting 0. Delete the lock by hand; check for a surviving process first
  (`pgrep -af <job>`) before assuming it is stale.

## Chrome restart is recovery, not a fix

Restarting Chrome (keeping `--user-data-dir`, so logins survive) clears a wedged
browser socket immediately. But the wedge is **load-induced**, so without the
lock it returns within hours. "Restarted and it works" is a fix that expires the
same afternoon.

## Half-migrated code is the real hazard

A job ported to raw CDP while its **helper functions** still call Playwright
looks healthy and hangs anyway — the hang just moves to the helper. This is
exactly what happened: the post/reply path was migrated, but the pacing-floor
timestamp read was not, so the tick stalled 180 s inside a "check that we are
not posting too often".

When migrating a job to a new transport, grep for **every** browser call in the
tree, not just the main one. `grep -n "connect_over_cdp\|sync_playwright" *.py`
answers the question directly.

## The generalisable lesson

The error named the transport, so the transport got blamed. The signal that was
missing was **"is anything else driving this browser right now"** — check that
before concluding a tool is broken. A tool that fails only under concurrency is
telling you about the concurrency.
