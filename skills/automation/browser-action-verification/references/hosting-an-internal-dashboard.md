# Hosting an internal dashboard that shows what an agent did

Class of task: "make a dashboard where you add the post link for every comment
and like" on a surface that must **not** be public. The rows are prospect names
and counts — the dashboard is a management instrument, not a product.

## Build the data first, the web surface second

A CLI view (`dashboard.py --activity 24`) is the reference implementation and the
test harness. Serve it, but keep it runnable without the server — when the port
is squatted or the unit is crash-looping, the CLI still answers.

Rows need: `ts`, `platform`, `action` (`like` / `comment` / `reply` / `follow`
/ `connect`), `target`, `url`, and a `text` field. The ledger already exists —
the per-run log is the same thing read as rows. **Do not build a second source
of truth for actions that already ran.**

## Ask before inventing a URL

On X the permalink is free: `https://x.com/i/status/<id>` resolves without auth
even if you only know the id. Follow the redirect and confirm the final URL is
the permalink you expected:

```bash
curl -s -o /dev/null -w "%{http_code} %{url_effective}\n" -L "<url>"
# 200 https://x.com/leo_mercerr/status/2105300196783423560
```

That check is what separates a real post link from a constructed one. Report it
as evidence — `status=200 final=<permalink>` — not as "the link works".

LinkedIn has no card-level permalink (see SKILL.md for the measurement). Ship
the text + a stated reason, not a blank. Offer the slow open-each-post pass as
an explicit trade-off.

## Backfilling a missing permalink: the extractor AND its verifier both lie

When links are missing because the *writer* never captured them, the repair has
two independent bug surfaces. Both bit in the same session — a first attempt
produced two confidently wrong URLs, and a follow-up verifier then declared
correct data "MISMATCH". Almost "fixed" good data based on a broken check.

**Bug 1 — the writer scraped the wrong attribute.** A confirm step did:

```python
body = pg.evaluate("()=>document.body.innerText||''")
m = re.search(r"/%s/status/(\d+)" % HANDLE, body)   # always None
```

X renders the status id **only in the `href` attribute**, never as visible text.
That regex returned `None` on every run, so every post was stored linkless and
the surface looked like a display bug rather than a capture bug. Fix: read the
attribute, and take the **first** `/status/` link in the article — later ones are
`/analytics`, quoted posts, and quoted-post parents.

```javascript
const l = [...a.querySelectorAll('a[href*="/status/"]')]
           .map(x => x.getAttribute('href') || '')
           .filter(h => h.startsWith('/' + HANDLE + '/status/'));
const id = (l[0] || '').match(/\/status\/(\d{15,25})/);   // [0], not "find any"
```

Narrow to our own handle so a pinned or quoted post cannot supply the wrong id.

**Bug 2 — the backfill matched on a too-short prefix.** A 30-character prefix
matched the wrong article and attached a plausible-looking permalink to both
posts. Prefix matching on social text is unsafe: posts share openings. Match on
a **70-char slice**, and reject on no-match rather than guessing.

**Bug 3 — the verifier was itself broken, and that is the dangerous one.**

```python
s.goto(url, settle=8)
arts = s.ev("[...document.querySelectorAll('article')]...") or []
hit = any(needle in a for a in arts)          # arts == [] -> "MISMATCH"
```

Eight seconds was not enough for the article to render, the list came back
**empty**, and the comparator printed `MISMATCH` for both — *correct* URLs. I was
one step from reverting good data on the authority of a check that had never
looked at anything.

**Rules that follow:**

- **When a verifier reports total failure, suspect the verifier first.** All-N
  failing is the signature of a check that inspected nothing, not of data that is
  uniformly wrong. Make the check report *what it saw* (`articles=N`, the first
  article's text) so "found nothing" is distinguishable from "found the wrong
  thing".
- **A negative result must be corroborated before you destroy anything.**
  Re-run with a long settle, and cross-check on a second independent signal
  (HTTP 200 + the expected text present on the page).
- **Print the matched text next to every write.** The log line that proved the
  data was right all along was `matched: My browser automation broke 4 times
  today` sitting right there in the backfill output.
- **Never revert good-looking data on one unverified check.** Write to a copy,
  diff, verify, then commit.

## A row cap silently hides older rows

`limit=30` on a 24h window looked like *"my posts are not being tracked"* —
they were rendered, just cut. 133 engagement rows existed in 24h; at 60 the
oldest row was **48 seconds newer** than the post, so raising the cap to 60
still dropped it.

Diagnose by comparing counts, not by reading output:

```python
for lim in (30, 60, 200):
    rows = activity(24, lim)
    print(lim, len(rows), sum(r['act'] == 'posted' for r in rows))
#  30  30 0      <- nothing renders
#  60  60 0      <- still nothing
# 200 133 2      <- both present
```

A saturating result that changes with the limit is a **cap** problem, not a
data problem. Default limits are the trap; size them above the measured daily
row count and note the measurement in the code.

## Surface the runs that did nothing

A timeline that only shows successes answers "when were you engaging" with a
misleading yes. The no-op ticks are the ones the user is actually asking about —
a tick that logged "nothing due" must render as a visible empty slot, not be
omitted. Distinguish *did work* / *correctly did nothing* / *failed* with
distinct outcomes in the row, and let a failed tick look different from an idle
one.

## Auth: three cases, from the public URL

The single highest-value check in this whole class of task, and the one most
routinely skipped. See the SKILL.md pitfall for the nginx-bypass mechanism.

```bash
U=https://<public-url>; PW=$(cat .dash_pw)
curl -s -o /dev/null -w "no-auth  %{http_code}\n" --max-time 40 "$U/healthz"          # 401
curl -s -o /dev/null -w "bad-auth %{http_code}\n" --max-time 40 -u "kunal:wrong" "$U/healthz"  # 401
curl -s --max-time 40 -u "kunal:$PW" "$U/healthz"                                       # 200
```

Run all three from the **public** URL. A localhost-only pass is what let an
unauthenticated 200 ship in this session.

Permission check that separates auth misconfiguration from an app crash:

```bash
sudo chown root:nginx /etc/nginx/.dash_htpasswd && sudo chmod 640 /etc/nginx/.dash_htpasswd
sudo -u nginx test -r /etc/nginx/.dash_htpasswd && echo readable
```

## Verify the unit, not the port

A stale hand-launched copy of the same server held the port; the systemd unit
had been crash-looping and serving pre-deploy code the whole time. A route added
minutes earlier 404'd — that mismatch is the diagnosis, and it also invalidates
the earlier "it's live" claim. Kill the stray pid, then demand `NRestarts: 0`
and a fresh `ActiveEnterTimestamp`.

## Handing over

Give the URL, the username, and **where the password lives on disk** (not the
password in chat — that widens the blast radius of the transcript). Then state
the two limits plainly, because both are true and the user cannot infer them:

- a `trycloudflare.com` hostname changes on restart and has no uptime guarantee
- rows before the code change have no link and cannot be backfilled

Offer the permanent named tunnel as the next step rather than leaving a
temporary URL looking like a finished address.
