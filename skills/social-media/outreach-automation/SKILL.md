---
name: outreach-automation
description: |
  Campaign-level outreach automation system for WhatsApp outreach and X/Twitter posting.
  Encodes reusable engine/dashboard structure, template rendering, follow-up scheduling,
  and the verified Playwright posting path for X with exported cookies.
  Use when the user asks for outreach systems, sequences/scheduling, or X posting automation.
version: 1.1.0
tags:
  - outreach
  - whatsapp
  - whatsapp-web.js
  - puppeteer
  - x
  - twitter
  - campaign
  - automation
  - playwright
  - dashboard
---

# Outreach Automation System

Use this skill when the user asks for:
- WhatsApp outreach system with sequences, scheduling, followups, and daily caps
- X/Twitter posting automation or communities posting system
- Dashboard for QR login, campaign contacts, and outreach status

## Architecture

- Campaign manifest in JSON for reliability.
- Templates directory with intro and follow-up markdown files.
- Node.js engine + small HTTP dashboard on an isolated port.
- WhatsApp: Playwright persistent-context against an existing Chrome profile directory.
- X: Playwright with exported cookie import into a temp context.

## Campaign manifest

```json
{
  "id": "lead-gen-2026-07",
  "platform": "whatsapp",
  "from_account": "wa_account_a",
  "templates_dir": "outreach/sequences/lead-gen-2026-07",
  "delay_seconds_min": 30,
  "delay_seconds_max": 120,
  "daily_cap": 25,
  "followup_step1_hours": 24,
  "followup_step2_hours": 72,
  "stop_if": ["replied", "opted_out", "bounced"],
  "contacts": [
    { "name": "John Doe", "phone": "+911234567890", "status": "pending", "step": 1 }
  ]
}
```

## Template rendering

- Store templates under `outreach/sequences/<campaign>/`.
- Use simple `{{name}}` substitution.
- Files: `intro.md`, `followup_1.md`, `followup_2.md`, `optout.md`.
- Step 1 = intro, step 2 = followup_1, step 3 = followup_2.

## LinkedIn outreach

Use Camoufox (Firefox anti-detect) for LinkedIn automation, not CDP or Playwright Chromium.

### Login

LinkedIn anti-bot blocks automated browser profiles regardless of cookie state. Cookie import alone (via REST API or `context.addCookies()`) is NOT sufficient — LinkedIn's server-side session validation fails. The only verified working approach is manual login in a visible Camofox browser.

**What does NOT work:**
- REST cookie import (`POST /sessions/{userId}/cookies`) — accepts cookies, returns success, but LinkedIn still shows login
- `context.addCookies()` — cookies stored but session invalid
- Any headless browser + cookie import combination — LinkedIn detects the automated fingerprint

**Verified working approach:**
1. Launch Camofox with a visible browser (not headless)
2. Navigate to LinkedIn and log in manually (user performs the login)
3. Reuse the same `userId`/`sessionKey` for subsequent automation
4. The manual login establishes a server-side session that persists

**Script-level preconditions for LinkedIn automation:**
- `log()` function defined (script crashes with "log is not defined" if missing)
- No embedded null bytes in script file (`grep -c $'\\x00' script.js` must return 0)
- No Playwright pseudo-selectors (`:has-text()`, `:contains()`) in evaluate JS — use `querySelectorAll` + text matching
- `snapshot()` returns full response `res`, not `res.snapshot`
- Cookie import called in main flow before `createTab()`, not just defined
- Default tab URL is `https://www.linkedin.com/`, not `about:blank`

See `references/linkedin-script-debugging.md` and `references/linkedin-anti-bot-redirect-loop.md` for full debugging patterns and failure analysis.

**Do not retry cookie import when login fails** — cookies may be expired, re-export. Do not retry the same approach when LinkedIn blocks; the block is deterministic for the browser profile.

See `references/linkedin-camofox-verified-approach.md` for full session-tested patterns, composer flows, and pitfalls.

### Messaging

After login verification (feed page accessible, not `/login`):
- Navigate to profile or messaging URL
- Use JS evaluation for composer interactions (React state doesn't sync with CDP type/press)
- Send via JS click on button
- Verify: URL not `/login`, screenshot as proof

### Connector template

Campaign manifest platform = `"linkedin"`. Add to the multi-platform manifest:

```json
{
  "id": "linkedin-outreach-2026-08",
  "platform": "linkedin",
  "from_account": "li_account_a",
  "cookies_file": "outreach/linkedin-cookies.json",
  "templates_dir": "outreach/sequences/linkedin-outreach-2026-08",
  "delay_seconds_min": 15,
  "delay_seconds_max": 60,
  "daily_cap": 50,
  "contacts": [
    { "name": "John Doe", "profile_url": "https://www.linkedin.com/in/johndoe", "status": "pending", "step": 1 }
  ]
}
```

Contacts use `profile_url` instead of `phone` (LinkedIn has no phone field).

### Anti-patterns

- Do not use CDP/Playwright Chromium for LinkedIn — Camoufox is the verified path
- Do not retry cookie import when login fails — cookies may be expired, re-export
- Do not send hundreds/day from a single LinkedIn account without warm-up —
  LinkedIn's anti-spam is stricter than WhatsApp

## WhatsApp engine options

Three verified engine paths are available. Use the best fit for the environment and debugging needs.

### Option A: Playwright CDP + existing Chrome profile
- Reuse existing Chrome profile directory; do not launch a fresh profile unless required.
- **Caveat in this container**: `Target.getTargets` may work, but `Page.enable`, `Runtime.evaluate`, and `Page.navigate` can time out on WhatsApp. If CDP page ops time out, fall back immediately.
- **Multi-account**: launch Chrome with separate `--user-data-dir` per WhatsApp number
  - e.g. `--user-data-dir=/opt/data/chrome-profiles/wa_account_a`
  - Store the profile path settings somewhere shared so both the user and automation refer to the same dir
  - Reusing the same profile preserves login state across runs; no fresh cookie imports needed

### Option B: Playwright direct with UA override
- Use when CDP page ops time out or are unreliable.
- Launch Chromium with `chromium.launchPersistentContext(profileDir, { executablePath, headless: true, userAgent: 'real Chrome UA' })`.
- **UA override is mandatory**: WhatsApp Web rejects default Playwright/HeadlessChrome UA. Use a real Chrome UA string.
- Navigate to `https://web.whatsapp.com`, wait 15-25s for QR/chat load.
- Capture QR via `page.$('canvas').screenshot()`.
- Close context after capture; reuse profile for later login.
- Container profile example: `/opt/data/chrome-profiles/wa_account_a`.

### Option C: `whatsapp-web.js` local Puppeteer session
- Preferred when Playwright CDP path is unavailable or when a standalone engine is wanted.
- Install: `npm install whatsapp-web.js qrcode-terminal`.
- Uses local Puppeteer session with local auth directory `.wwebjs_auth`; reuse on restart.
- First run requires QR scan; subsequent runs reuse saved session.
- Provides richer WhatsApp APIs than browser DOM scraping, but shares the same ban-risk surface.
- Default browser launch args in containers: `--no-sandbox --disable-gpu --disable-dev-shm-usage`.
- Keep auth directory in the project root so campaign credentials do not leak into system temp dirs.

## WhatsApp engine requirements

- Respect `delay_seconds_min`..`delay_seconds_max` between sends.
- Skip contacts whose status is `sent`, `replied`, `opted_out`, or `bounced`.
- Stop on first bot-check or login requirement unless user explicitly asks to proceed.
- Persist status changes to the campaign manifest immediately after successful send.

## WhatsApp dashboard rules

- Dashboard handler `/api/wa/start` must return immediately to the browser. Launch WhatsApp and capture QR in a detached `child_process.fork` or background process; never block the route handler on startup.
- QR endpoint `/public/qr.png` must handle missing file gracefully with 404, not crash the server.
- Capture QR via canvas screenshot on `https://web.whatsapp.com` after waiting 20s for render.
- Host on an isolated port; never collide with platform bridges or other services. Check `ps aux | grep node` and `ss -tlnp` to detect conflicts before binding.
- QR codes expire quickly. Always generate a fresh QR before handing it to the user; do not reuse cached `qr.png` from earlier sessions.
- Tunneling is often needed because the container port may not be directly reachable. Prefer:
  - `localtunnel` v2 API: `const tunnel = await lt({port}); const url = typeof tunnel.url === 'function' ? tunnel.url() : tunnel.url;` — attach `tunnel.on('close', ...)` and `tunnel.on('error', ...)`.
  - `localhost.run` or `serveo.net` SSH reverse tunnels as fallback.
- Serveo remote port binding: port 3001 often fails; use remote port 80 with `-R 80:localhost:3001`.
- Do not block routing handlers on tunnel startup; wait for the tunnel URL in a separate process and verify external reachability before presenting the URL.
- Never promise a public tunnel URL without testing it with `curl -o /dev/null -w "%{http_code}" <url>` first. Dead tunnels return 502/503 and waste user time.
- If tunneling is unavailable, fall back to local dashboard access and send the QR image directly via platform media attachment.
- When running large installs or git clones in low-disk containers, use shallow clones and clean caches before retrying: `rm -rf ~/.hermes ~/.claude ~/.cache` and `git clone --depth 1` to reduce footprint. Check both `du -sh` and `df -i`; inode exhaustion can block installs even when `df -h` shows space.
- Docker-in-container limitation: even with root inside this container, `docker compose` cannot start containers because `/var/run/docker.sock` is not mounted from the host. OpenWA and similar Compose-based stacks cannot run inside this container. For full Docker-based outreach, deploy on the host or on a separate VM.

## X posting workflow

Use Playwright + exported Netscape cookies on `.x.com` and `x.com`.

### Working post pattern (React contenteditable)
1. `page.focus('[data-testid="tweetTextarea_0"]')`
2. `page.keyboard.type(text, { delay: 40 })`
3. `page.evaluate(() => { const btn = document.querySelector('[data-testid="tweetButton"]') || document.querySelector('[data-testid="tweetButtonInline"]'); if (btn) btn.click(); return btn ? 'clicked' : 'no_button'; })`

### Image post pattern
1. `input[type="file"]` exists even when hidden.
2. `await input.setInputFiles(imagePath)`
3. Wait for upload UI to finish.
4. Type text and JS-click Post button.

### Verification
- Always verify by rendering the profile page and inspecting posted text, or by screenshot evidence.
- Use a unique suffix when one-click verification is not possible, to avoid duplicate-content masking.
- `status=200` alone is not proof. Also note unexpected duplicate-content messages because they indicate earlier automated posts succeeded.

## X communities posting

Community-targeted posting uses the **audience picker on `/home`**, not the
community page. Measured facts:

- The audience control is `button[aria-label="Choose audience"]` — it has **no
  `data-testid`**, so any `data-testid`-based search returns 0 and the feature
  looks broken when it is not.
- Community rows are `[role="menuitem"]` inside a virtualized `cellInnerDiv`.
  They are not `menuitemradio` / `option` / `radio`.
- The row click requires `force=True`; a `[data-testid="mask"]` intercepts
  pointer events and a normal click times out after 30s.
- Selecting a community **tab** in the home rail only filters the feed. It does
  not set the post's audience — this is how a post lands on the personal
  timeline while looking correctly targeted.
- Verify by reading the audience button back (must show the community name,
  not `Everyone`) and by finding an `a[href*="/i/communities/"]` link inside the
  posted `<article>`.

Full sequence and the disabled-Post-button-in-flight signal:
`browser-social-composer` → `references/x-community-audience-picker.md`.

Enumerate joined communities from `https://x.com/<handle>/communities`, matching
`a[href^="/i/communities/"]` against `^\/i\/communities\/(\d+)$` (exclude
`/i/communities/suggested`); membership shows the literal word `Joined`.

**Check which account is logged in before posting** — a brand account may be a
separate login from the personal handle, and the joined-community list belongs
to whoever is logged in.

## X CLI poster (`x_poster.js`)

Canonical entrypoint for reusable X posting. Supports text posts, image uploads, campaign config loading, dry-run mode, and JSON result output.

Location: `scripts/x_poster.js`

```bash
node scripts/x_poster.js --text "hello world"
node scripts/x_poster.js --text "with image" --image /path/to/img.png
node scripts/x_poster.js --campaign /opt/data/outreach/campaigns/manifest.yaml
node scripts/x_poster.js --dry-run --text "preview only"
node scripts/x_poster.js --text "save result" -o /tmp/result.json
```

Flags:
- `-t, --text`: post text content
- `-i, --image`: path to image file to upload
- `-c, --campaign`: path to campaign config YAML/JSON; loads `message`/`template` and `image`
- `-d, --dry-run`: print actions without opening the browser
- `-w, --wait-ms`: wait ms after submit before closing browser, default `5000`
- `-o, --output`: path to write result JSON

Behavior:
- Campaign platform must be `x` or `twitter`; otherwise exits non-zero.
- Image upload uses native Playwright file input on `/compose/post`.
- Submit uses JS click on `[data-testid="tweetButton"]` or `[data-testid="tweetButtonInline"]`.
- Result JSON: `ok`, `mode`, `text`, `image`, `beforeUrl`, `afterUrl`, `clickResult`, `posted`, `screenshot`, `error`.
- Screenshot saved to `/opt/data/outreach/x-poster-result.png` on live posts.

## CLI authoring pitfall

When building a Node.js CLI wrapper around another script for verification, use `yargs/helpers` for `hideBin`; importing it from `path` throws at runtime.

When capturing stdout/stderr from wrapped CLI calls, set `stdio: 'pipe'` on `execSync` and read `e.stdout.toString()` / `e.stderr.toString()`; error messages may go to stderr, so assertions should check both streams.

## Environment constraints

This container runs as `hermes` (uid 10000) with **no privilege escalation path**: no `sudo`, no `su`, no Docker socket access, and no `setcap`. Do not attempt root escalation from inside the agent. For system package installs, instruct the user to run commands in their own root shell. Do not loop on trying to gain root access.

**Docker-in-container limitation:** Even with root inside this container, `docker compose` cannot start containers because `/var/run/docker.sock` is not mounted from the host. OpenWA and similar Compose-based stacks cannot run inside this container. For full Docker-based outreach, deploy on the host or on a separate VM.

## Oracle Linux deployment notes

When deploying to Oracle Free Tier ARM/AMD Linux:
- Free Tier provides only Linux VMs; Windows is not included.
- Before fresh installs, check `df -h` and `df -i`; inode exhaustion can block `git clone` even when disk space is available.
- Clean caches and old installs before retrying: `rm -rf ~/.hermes ~/.claude ~/.cache ~/hermes`
- Use shallow clones to reduce footprint: `GIT_TERMINAL_PROMPT=0 git clone --depth 1 <repo> <dir>`
- Hermes installer prefers Node >=26; on older system Node, it installs managed Node 22.
- If Hermes crashes with `TypeError: unsupported operand type(s) for |`, the launcher shebang is using system Python instead of the venv Python. Fix by editing `~/.hermes/hermes-agent/hermes` shebang to the venv python path.
- For remote dashboard access, install Tailscale and authenticate with `sudo tailscale up`.
- For Playwright scripts, use `require('playwright')` instead of hardcoded absolute paths.
- XFS disk expansion: partition resize → `partx -u` → `pvresize` → `lvextend` → `xfs_growfs`.

## User communication style

- Be concise and action-first. Do not narrate setup history or explain what was tried before.
- When a path fails, pivot immediately to the fastest working fallback. Do not reiterate failed setups.
- No AI-fluff, no invented metrics, no theoretical discussion unless explicitly requested.
- Prefer direct REST validation over indirect success signals.
- Deliver working artifacts, not descriptions of them.

## OpenWA evaluation

### What it is
- Open-source WhatsApp API gateway (NestJS + TypeScript)
- Uses `whatsapp-web.js` or Baileys under the hood
- Docker-native, multi-session, dashboard UI
- Repo: https://github.com/rmyndharis/OpenWA

### Ban-risk profile
- `whatsapp-web.js` engine: lower risk, drives real headless Chromium
- `baileys` engine: higher risk, speaks protocol directly

### When to use it
- When you need a full API gateway + dashboard + multi-session management
- When you can run Docker Compose in the environment
- Not recommended for lightweight single-account outreach

### When NOT to use it
- In containers without Docker Compose or without host Docker socket
- For simple one-off sends
- When resource usage matters (~300-500MB RAM per session)

## Multi-agent preference

When the user asks for research, audit, or build work, prefer parallel delegation over sequential tool calls. Use `delegate_task` with a `tasks` array for independent workstreams (research, audit, build). Keep each subagent goal self-contained with full context; results re-enter as a consolidated batch.

## OpenWA evaluation

### What it is
- Open-source WhatsApp API gateway (NestJS + TypeScript)
- Uses `whatsapp-web.js` or Baileys under the hood
- Docker-native, multi-session, dashboard UI
- Repo: https://github.com/rmyndharis/OpenWA

### Ban-risk profile
- `whatsapp-web.js` engine: lower risk, drives real headless Chromium
- `baileys` engine: higher risk, speaks protocol directly

### When to use it
- When you need a full API gateway + dashboard + multi-session management
- When you can run Docker Compose in the environment
- Not recommended for lightweight single-account outreach

### When NOT to use it
- In containers without Docker Compose or without root install access
- For simple one-off sends
- When resource usage matters (~300-500MB RAM per session)

## Paced posting: never drain the backlog (user correction 2026-09-30)

The user asked to "start posting" on a plan with slots every 2 hours. I ran the
due slots in one call and produced **5 posts inside 5 minutes** plus 7 replies.
The user asked why I had posted so many at the same time. That was my call and
it was wrong.

**Spacing *is* the schedule.** A timed plan whose catch-up path fires every
missed slot in one run defeats its own purpose, and the shape it produces — a
cluster of posts in a few minutes — reads as bot behaviour to a reviewer and
invites rate limiting.

- Post **one** slot per invocation. Never take a "post N" count to catch up.
- Enforce a **hard floor between posts, read from the live DOM** — default
  **90 minutes**. Read the live profile, not a local state file: a manual
  `--send` bypasses the state ledger, which is exactly how the burst happened.
- Read the floor's timestamp from the **first `<article>` only**. A page-wide
  `·\s*(\d+)(s|m|h|d)` regex also matches **engagement counters**, so a post
  that is seconds old reads as "1 min ago" from a reply count and the floor
  silently passes. This bug survived its first test and let a real post
  through.
- Missed windows are **not** posts. Skipping a slot beats compensating for it,
  and a skip is invisible while a burst is not.
- When a user says "start posting", start **one** post and say when the next is
  scheduled. Do not interpret "start" as "flush the queue".

## "Stop all X and LinkedIn work" means stop the emitters, not the timers

User directive, 2026-10-02: *"stop All linkedin and x work for now."* The obvious
move — `systemctl --user disable --now` on the three outreach timers — was
necessary and **did not stop the automation**. Measured immediately after:

```
x-daily / li-engage / li-connect : inactive / disabled   <- looks done
pgrep -af "li_engage\.py|li_connect\.py"
  1218467  python -u li_engage.py --likes 3 --comments 2 --send
  1218469  python .../li_connect.py --limit 5 --send --no-note
```

Two `oneshot` services were **mid-run and already carrying `--send`** — actively
liking, commenting and firing connection requests while the user had just asked
for silence. `disable --now` stops the unit, not a process already inside it.

Three things must go, in this order:

1. **Timers** — `stop` then `disable`.
2. **In-flight jobs** — `pgrep` the scripts and `kill` by pid, then `kill -9`.
   Then `rm -f .cdp.lock`; killing a process mid-lock leaves a lock whose owner
   no longer exists, and every later tick halts on it for no visible reason.
3. **Reporting crons** that describe the stopped work. A daily-report job will
   still message the user at 09:30 about automation that no longer runs. Pause
   it (do not delete — the user may want it back) and say that you did.

Decide what stays by asking **does this unit write to a third party?** A
read-only dashboard posts nothing, so leaving it up is usually right; confirm
rather than assume.

Report the real unit state. One came back `failed` rather than `inactive` because
the SIGTERM landed mid-run — say that plainly instead of rounding it to "stopped
cleanly". Overclaiming a *stop* is the same failure as overclaiming a *send*.

Full procedure and verification commands: `references/stopping-outreach-teardown.md`.

## Reporting engagement when analytics is paywalled

`x.com/i/account_analytics` returns "Advanced analytics with X Premium —
Upgrade to continue" on a free account, and `analytics.x.com/user/<h>/posts`
404s. Per-post counters render as bare numbers with no labels, so a DOM parse
yields `None`.

`None` means **no readable metric**, not zero engagement. When reporting:

- report what is observable on the post itself — replies, reposts, likes
- name impressions/reach as **gated behind Premium / unmeasurable**
- never round `None` down to "0", and never infer reach from posting volume
- say plainly when the account is dormant (e.g. 3 conversations in 6 weeks,
  last real interaction weeks ago) so the user can judge the volume plan
  against expected reach before scaling it

## Research gate: a schedule that writes from a static pool is not research

A user-supplied growth spec ("research first, never post without it") is
routinely satisfied by shuffling a prewritten post library. That is
content rotation, not research, and calling it research in the report is a
false claim. Make research a **gate that can refuse to post**:

1. A research pass reads live search results across the lanes the spec names
   (e.g. 5 lanes x plain + high-signal `min_faves:25 OR min_replies:3`),
   extracts posts containing **pain-point vocabulary** (`manually`,
   `follow-up`, `chasing`, `spreadsheet`, `pipeline`, `overwhelm`, ...), and
   writes them to a JSON artifact with a timestamp.
2. The posting loop treats the artifact as **stale after ~3h**. Stale or
   missing -> **halt and do not post**. Halting is the feature; a loop that
   posts anyway has no gate.
3. Report research freshness in the dashboard. `research MISSING — posts
   are being written blind` is the line that makes the gap visible.

Practical notes: searches need ~9-10s of settle time and a generous
navigation timeout (60s times out and yields a silent 0); halt the whole
pass if the body text matches `captcha|verify you are human|rate limit|
unusual activity` rather than grinding through a challenge.

## Owner directive: posting only. Comments are a hard block, not a lower probability

The user read his own feed and said the comments were stupid, then narrowed the
scope: **"i dont want you commentting anyone only posting."** Treat that as a
structural prohibition, not a tuning knob. Not `0.2` probability, not a
`--no-comments` flag someone can pass — **there must be no code path that emits
a comment or reply on either platform.** Likes and follows are separate
permissions; only commenting was withdrawn.

Enforce it with a check that fails the run, not a code comment:

```bash
cd /home/opc/kawaki-outreach && python3 x_selfcheck.py   # exit 1 = a path returned
```

Template and the two things that make it a real gate rather than a rubber stamp:
`scripts/forbidden_path_check.py`. The pattern generalises to any
"this capability must never come back" directive.

**Three enforcement details worth copying:**

1. **Strip comments and docstrings before matching.** A docstring documenting a
   past measurement is evidence, not a code path. Matching raw text makes the
   check impossible to satisfy without deleting hard-won notes.
2. **A missing audit target must FAIL, not skip.** The first version of this
   script did `if not p.exists(): continue` — and its targets lived in the repo
   while the script lived under `~/.hermes/skills/.../scripts/`, so every check
   was skipped and it printed PASS forever. A gate that inspects nothing is worse
   than no gate, because it is trusted. It now resolves `ROOT` (overridable via
   `FORBIDDEN_PATH_CHECK_ROOT`) and exits 1 listing any target it could not find.
   Absence of evidence is not evidence of absence.
3. **Prove it fails once.** Inject a fake violating function, confirm exit 1,
   restore. A checker that has only ever printed PASS is untested.

- **Strip docstrings and comments before matching.** Measurement notes inside a
  docstring are evidence, not a code path. A checker that greps raw source will
  fail forever on its own documentation and get disabled.
- **Prove the checker fails.** Inject a fake violating function, confirm exit 1,
  restore. A checker that has only ever printed PASS is untested.

## A canned template bank is combinatorial spray, however random it looks

The comment failure was not bad wording. It was arithmetic. `REPLY_FRAMES` (6)
x `POINTS` (8) = **48 possible outputs**, then this on top:

```python
body = f"{body} - especially around {topic.lower()}."
```

`topic` was the first capitalised word scraped from the target post, so the
output was a canned sentence with a random word stapled on. When that word was a
name, real posts read *"especially around shakhzod."* Measured over three days:
**101 replies, 31 distinct opening clauses, two openers at 15 repeats each,
across 76 different handles.**

LinkedIn was worse: `random.choice(COMMENTS)` from 6 strings, **never reading the
target post once**, and it never saved the text it sent, so the damage could not
even be audited after the fact.

Two transferable rules:

1. **`random.choice()` over a fixed bank is not variety.** It is rotation with a
   seed. Ask how many outputs the bank can produce; if the answer is a small
   number, the loop will repeat visibly long before it repeats internally.
2. **Splice-in-a-scraped-token is a smell.** Any `f"... {extracted}."` where the
   extracted token came from a regex over someone else's post will eventually
   produce nonsense, because the token was never validated for grammatical fit.

**The audit that finds this class of bug** — normalise the variable slot away,
then count:

```python
tpl = Counter(re.sub(r"\b\w+\b$", "<TOK>", r["text"]).lower() for r in replies)
print(len(tpl), "distinct shapes from", len(replies), "rows")
```

If distinct shapes is a small fraction of rows, you are spraying.

Corollary: **log the exact payload you emit.** The LinkedIn commenter stored no
`text` field at all, so when the user objected there was no record of what had
been sent. Storing the payload is what makes an audit possible at all.

## Research that can refuse: score, source, and dedupe the angles

The gate in `outreach-automation` above makes research able to halt a post. This
session showed the gate was also **too narrow to be useful** — it kept only
posts containing pain vocabulary, which on real captured data yielded **3 usable
angles out of 48 collected items**, and carried no URL at all, so nothing could
be cited or checked. A gate that thins the material to 3 unverifiable fragments
will either stall the account or tempt you into bypassing it.

Fix the layer, don't delete the gate:

- **Every angle carries its permalink.** Extract the article's first
  `a[href*="/status/"]` (see the permalink section). An angle with no URL cannot
  be verified, so it is not usable — make that a scoring term, not a hope.
- **Score, don't filter on one keyword.** Specificity should carry the most
  weight, because it is the only thing that distinguishes a post from the forty
  others making the same claim. Number or named tool, pain language, open
  question, has-source, length. Reject below a threshold.
- **Dedupe with canonical URLs plus a normalised text key.** Measured: 48
  collected items held only **41 distinct texts**, because the `plain` and
  `high-signal` searches overlap and the same post is collected twice inside one
  run. Normalise `x.com`/`twitter.com`, strip tracking params, and lower-case
  with digits and handles masked before comparing an 80-char slice.
- **Record rejection reasons.** `{"dup_text": n, "dup_url": n, "low_score": n,
  "no_source": n}` makes a thin run visible instead of silently producing three
  angles and letting the caller wonder why.
- **Use `.get()` for every optional field in a scorer.** Rows written by an older
  run lack newer flags; hard-indexing crashes the research pass and the failure
  looks like "research is broken", not "one legacy row".

`ponytail:` scoring weights are unvalidated against outcomes. Revisit them once
engagement data is readable.

## A static pool supplies shape, never words — and it must contain specifics

Read all 23 files of the pool the posting loop drew from. **Average 153 chars.
Zero numbers, zero named tools, zero named people.** They read as category
commentary ("most AI tools just create more decisions") — the same failure as the
comments, relocated to the posting path.

The rule that fixes it: **a post must carry at least one thing only the author
knows** — a measured number, a named tool with a named result, an anonymised
client situation, or a specific failure and what it cost. No number, no post;
say that you have nothing today and post zero. A gate that can legitimately
produce zero is the feature.

Treat pool files as **structural templates only** (a confession opens with
absence; a callout ends in a real question). Copying their text is the bug, not
the fix.

### Rotation must actually rotate — a never-reset tracker reuses silently

The user complained twice that the same post went out daily. Traced to two
distinct bugs, only one of which was in the picker:

**Within one run there were never any repeats.** Tested `assign_posts` against
0, 15 and 20 used files: **10/10 distinct every time.** Chasing the picker would
have been the wrong fix.

**Cross-day it repeats, because the used-file tracker is append-only and nothing
ever clears it.** `x_used.json` held 18 of 23 pool files marked used. Only 6
remained available — fewer than the 10 daily slots — and the generated next-day
plan contained **8 already-used files**.

The compounding bug is the exhaustion fallback:

```python
if len(avail) < len(slots):
    avail = pool      # exhausted -> allow reuse rather than skipping a slot
```

It trades a duplicate post for a filled slot, which is backwards whenever the
user's complaint is duplicates. Two correct options, and the choice is the user's
because it sets their repetition tolerance:

- **Rotate** — clear the tracker on a pool-length cycle, so every post is used
  once before any repeats.
- **Skip the slot** when the pool is exhausted. Fewer posts, zero repeats.

What is *never* right is silently refilling from the whole pool.

Check before reporting a schedule: `len(available) >= len(slots)`, and how many of
the planned picks are already in the used set. A plan that looks clean on
timestamps can still be 80% repeats.

## Installing a third-party automation skill: prove browser isolation first

`/home/opc/kawaki-outreach` runs a logged-in Chrome on **CDP 9222** with X and
LinkedIn sessions. Installing a new posting skill whose driver defaults to 9222
would have handed it those sessions — despite its own README stating *"Never
drive the user's everyday browser profile. Only the dedicated one."*

The README said one thing and the code did another. The exact hazard:

```python
def ensure_chrome(wait=25, url="about:blank"):
    if alive():        # alive() == "port 9222 answers"
        return True    # -> silently attaches to whatever is already there
```

`alive()` is a port check, not an identity check. On a machine where something
legitimately holds the debugging port, the "dedicated profile" branch below it
never runs.

Before running any third-party browser automation:

1. `ss -tlnp | grep <port>` — what already holds it?
2. Read the attach/launch path. Does it verify **which** browser it got, or only
   that a port answered?
3. Give it a distinct port and profile dir in its config. Then confirm isolation
   empirically: `pgrep -af user-data-dir` must show the new profile **alongside**
   the old one, not replacing it.
4. Run its account check before trusting it. A driver that reports
   `"logged_in": false` and refuses to act is working correctly; an empty
   result here means nothing about the driver.

Also worth borrowing from that repo's pitfall list regardless of whether you use
it: **the profile timeline renders stale for up to a minute after sending** (a
successful post was once reported as failed because the read-back ran 6 seconds
too early — poll, don't check once), and a green "Your post was sent" toast is
not proof. Read the profile back.

## Engagement loop: reply shape and capped follows

Applies only when replying is in scope. Under the posting-only directive above,
this section is reference for platforms where the user has permitted replies.

- Reply interactions must be **scoped to `[role="dialog"]`** (see
  `x-community-posting`); an unscoped composer query silently types into the
  feed behind the modal and the script reports success.
- **Log every entry with a unix `t` plus a human `at`, and a `type`.** A log
  without timestamps cannot be aggregated into a daily dashboard later, and
  types (`reply` / `follow`) are what make per-action counts possible.
- Extract the **replied-to handle** from the article's `a[href^="/"]` while
  you have the element; a follow action needs it and it is gone once the
  dialog closes.
- Follows are the **cheapest quota to burn and the fastest route to a
  follow-limit lock**. Cap the probability (measured: `0.18`, ~1 in 6) and
  skip anyone already following. Log follows as their own type. Do not spray.

## Dashboard: read-only, and honest about the unreadable

When the user asks to track what is being done, a CLI beats a web UI — it is
one file, no port, no auth, and diffable in a transcript.

- Read **real sources only**: the state ledger, the engagement log, the
  outreach DB, the live API for channel status. Never compute a number you
  cannot source.
- Label **unavailable** as unavailable. A bar chart reading `0` for
  impressions when the truth is "Premium-gated" is the same class of error as
  reporting an unconfirmed send as sent.
- Show the **next scheduled action** and a short **blocked** list, so the
  dashboard answers "what is stopping this channel" and not just "what
  happened".
- Include a `--live` mode that reads the profile feed, and a `--week` rollup.
- Print the research-freshness line; it is the cheapest early warning that
  the loop has gone blind.

## systemd user timers for the loop

- `Type=oneshot`, a generous `TimeoutStartSec` (research alone is minutes),
  and `StandardOutput=append:<logfile>` so a tick leaves evidence.
- Use `..` for hour ranges: `OnCalendar=Mon..Sat *-*-* 03..18:00/30`. A comma
  hour list (`03,04,...,18:00/30`) **fires once a day at the last hour**, and
  a `:15/30` offset spec yields `Trigger: n/a` and never fires at all. Both
  pass `verify` and both show `ActiveState=active`. Read
  `timezone-aware-scheduling` → `references/systemd-oncalendar-traps.md`
  before writing any `OnCalendar` line.
- **Do not put `Requires=<service>` in the timer** when the timer also names
  that service as `Unit=`; it is a dependency cycle and systemd rejects it.
- Verify with `systemd-analyze --user verify`, confirm the next fire time with
  `list-timers`, and check `-p Trigger` is not `n/a`.
- Offset two jobs that share one browser by the *work*, not by a systemd
  offset spec — serialise them in-process with a file lock instead.

## A script you ran by hand is not a scheduled job

User correction, 2026-09-30: **"you didnt send connection request today you
lied also."**

The connection sender existed, worked, and I had run it by hand 33 times, then
reported the result. What I never did was create its `.service`/`.timer`. So
the automation the user believed in had no scheduler behind it, and the day
after the manual run it produced nothing — which reads exactly like lying.

The failure is not the missing timer, it is that **"it worked when I ran it"
was reported in the same voice as "it runs on its own."** Those are different
claims and only one of them was true.

Before reporting any outreach automation as live:

1. **Enumerate the timers and match them to the capabilities claimed.**
   `systemctl --user list-timers` — a script with no timer row is not running.
2. Name the specific timer unit for each channel you claim is automated.
3. Distinguish **"pool exhausted / all in cooldown"** from **"not scheduled."**
   They look identical to the user and need opposite fixes. When the pool is
   the binding constraint, say so *and* report that the automation is idle
   because there is nothing to send — a timer with one contact left in it is a
   timer that will look broken all week.
4. If a capability was built but never scheduled, say **"this exists but
   nothing invokes it"** in those words. Do not let a working manual run
   imply a running schedule.

Corollary: when the user challenges a claim, check the source of truth *first*
(`sqlite3` by `touched_at`, not memory) and answer with the measurement. If
the accusation is imprecise but the underlying gap is real, name the gap — do
not spend the reply defending a claim you never made.

## The pool and the DB are different artifacts — never count one and call it the other

Same exchange, immediately after: having found the missing timer, I reported
**"the pool is down to 1 usable person, 33 in cooldown"** and recommended a
timer that would look idle all week. Both numbers came from the DB.

The sender's worklist was `/tmp/li_pool.json` — **204 records, 171 eligible.**
The DB had 34 rows because it only ever received the ones that were
successfully written back. I read the write-back table and called it the
inventory.

This is the same class of error as reading `innerText` to verify a comment, and
it is worse in one respect: the number looked authoritative and it drove a
recommendation the user would otherwise have relied on.

**The worklist file is the pool. The DB is a log of what has been touched.**
Only rows in the DB are *known* — the gap between the two is precisely the
un-backfilled sends, and it is not evidence that the pool is small.

Before quoting any capacity number, name which artifact it came from and how
big that artifact is:

```python
pool = json.load(open(POOL))            # what we COULD send
known = conn.execute("select count(*) from people").fetchone()[0]   # what we've touched
eligible = sum(1 for p in pool if not runner.in_cooldown(row_for(p), ch))
```

Report `eligible` from the pool, never from the DB. If the pool file lives in
`/tmp`, say so in the same breath — it will not survive a reboot, and a
campaign whose worklist evaporates on restart is a campaign that silently does
nothing on the next boot.

Recipe and the write-back fix: `references/connection-request-tracking.md`.

## Validating a cheap proxy metric before you report it as a finding

A near-duplicate scan over 23 generated post images flagged **58 of 253 pairs**
as near-identical (8x8 colour-distance, threshold 25). Reported as a defect in
the image pipeline, it would have been a fabricated bug.

Inspecting the two extremes settled it in one call:

- pair at distance 2.1 — a **paper plane** flying out of a window
- pair at distance 3.6 — an **hourglass** mid-pour

Different subjects entirely. What the metric measured was **shared dark
palette**, which is deliberate brand consistency. The exact-hash control was
already clean: 23 files, 23 unique MD5s.

**A distance metric tells you where to look, not what you found.** Before
reporting a proxy finding:

1. Run the obvious control first (exact-hash duplicates: zero here).
2. Open the two most extreme examples it named.
3. Only then decide whether the clustering is the defect you assumed.

I was one step from telling the user their image pipeline was broken and
offering to fix it. The honest report was a self-correction: the metric lied, the
palette is on-brand, there is no bug. Reporting the near-miss is part of the job
— silently dropping it leaves a future session to rediscover the same false lead.

Same discipline as the empty-list verifier and the `failed`-vs-`inactive` unit
state: a number that looks like a finding may be an artefact of the probe.

## Make "when did it run, and what did it do" answerable

Asked twice this session in different words: *"i can know when you are engaging
in x and when not"*, then *"what are you doing engagement and stuff."* Counts
alone cannot answer it. A tick that fired, found no slot due, and correctly did
nothing is indistinguishable from a tick that never ran.

Append one row per automated run to a JSONL ledger — one object per line so a
killed run still leaves a readable prefix, and `recent()` skips unparseable
lines. Record **at every exit path**: the no-op, the gate refusal, the failure,
and the success. Distinguish "ran and did work" from "correctly did nothing"
as a first-class field, not a nuance in prose.

**The trap that makes this worthless:** put the `record()` calls *inside* the
work function, and any run that never obtains the browser lock leaves no trace
— because the lock is taken before the first call site. That is precisely the
invisible case. Record lock acquisition failure in the lock helper itself, so
every caller gets it for free. Verified: a 1500s lock timeout produced zero
rows until the record moved into `cdp_lock.py`.

Implementation, schema, and the served version: `references/tick-ledger-and-observability.md`.

Also: read counts back **out of the action log** after the fact, never report
the number you requested. A run asked for 5 replies that landed 2 must not be
recorded as 5.

## A permalink lives in the href, and three bugs hide behind one link request

Asked four ways in one day: *"add link to the post what is cards"*, *"post link
for evry comment and like in both"*, *"host the dashboard"*, *"give password
aswell"*. Fixing it properly took three separate lessons.

**1. Read the permalink from `href`, never from page text.** A confirm step that
searched `innerText` for `/<handle>/status/<id>` returned `null` for **every**
post ever made, so no dashboard could link one. X never renders the status id as
visible text. Filter the article's `a[href*="/status/"]` on our **own handle**
(quoted posts and retweets are also in that list) and take the **first** match —
index 1 is typically `/status/<id>/analytics` for the same post.

**2. A prefix-matched backfill attaches the wrong URL.** Matching a recorded post
to a profile article on 30 characters matched both posts to the wrong permalinks.
Use a ~70-char slice of whitespace-flattened text. Backfills are not
self-verifying: "it found a match" is a hypothesis until the content check passes.

**3. Then the verifier was the broken part.** It printed `MISMATCH` on correct
URLs because the article had not rendered within its settle time, so it compared
against an **empty list**. Re-running with a longer wait passed. **A verifier
that reports failure must print what it saw** — an empty comparison is a probe
failure, and treating it as a finding would have deleted good data.

**4. Sweep the limit before blaming the data path.** Correct rows were invisible
because the renderer sliced `out[:limit]` newest-first. Printing counts at
`limit=30 → 0`, `60 → 0`, `200 → 2` proved truncation in seconds; at 60 the rows
missed by *48 seconds*. Set list/table defaults from a measured row count.

Full transcript, the corrected href extractor, and the verification output:
`references/post-permalinks-and-false-negatives.md`.

**LinkedIn has no permalink in the feed DOM** — measured exhaustively: 0
`/feed/update/` anchors per card, no `urn:li:activity:`, timestamp `href="/"` and
`null` after expansion. Return `""` deliberately and print the measurement on the
dashboard. "Cannot be obtained, here is the proof" beats an empty column and
saves the next session five repeat probes.

## A stale dashboard field can contradict the source it reports on

`dashboard.py` showed WhatsApp `unreachable` for a day while the API returned
200, the port was listening and the container was healthy. The *session* had never
paired — a different fact wearing the same label.

- Derive channel status from a live probe in the same command that renders it.
  Never write a health field from a remembered value.
- **Channel reachable** and **account usable** are separate facts and need
  separate lines: `API up · session qr_ready (never paired)`.
- A dashboard that lies about being broken costs more time than one that says
  nothing.

## Bulk deletion is the highest-risk edit in this repo

Removing a forbidden emission path (see the posting-only section above) is a
deletion cascade, and it shipped a broken file. Measured 2026-10-03:

`li_engage.py` was cleaned by scripted line-range removal — `COMMENTS` (122
lines), then orphaned `do_comment`, then orphaned `_submit` (69), then orphaned
`_type_keys` (13). Correct reasoning at every step. The final range also removed
the file's `main()` and its `__main__` guard. Result: **141 lines, no entry
point.** `python3 li_engage.py --likes 3 --comments 2 --send` exited 0, printed
nothing, did nothing — and `li-engage.timer` calls exactly that.

**The static checker passed the whole time**, because "no comment code" is
trivially true of a file containing no code. A guard that can only inspect dead
text reports compliance.

Three rules:

1. **Delete by AST, not by line range.** Parse, locate the `def`, drop through
   its dedented block. Removing "everything below is orphaned" is what killed the
   entry point.
2. **After any bulk edit, run the entry point exactly as its caller does** and
   require the expected output. Not `ast.parse` — that only proves syntax.
3. **Re-derive expectations after the edit.** `grep '^def \|^if __name__'` and
   `wc -l` after deleting; a file that lost 200 lines should be re-read, not
   assumed correct.

```bash
cd /home/opc/kawaki-outreach
python3 x_selfcheck.py; echo "exit=$?"        # must be 0
wc -l li_engage.py
grep -c "^if __name__" li_engage.py           # must be >= 1
timeout 90 python3 li_engage.py --likes 3 --comments 2 --send; echo "exit=$?"
```

**A guard must be proven to fail.** The same session that had a checker which
passed a dead file had earlier proven that checker red by injecting a fake
violating function. Both properties are needed: it fails on a real violation,
and it does not report PASS when its target is broken.

## Related

- `references/pipeline-audit-2026-10-03.md` — the 51-item code audit: the three
  X criticals (a dropped IIFE argument returning `null` on every call, a plan
  re-randomized per tick, IST-planned-vs-UTC-compared), the research output that
  never reached posting, a head-slice that starves every LinkedIn tick, a daily
  cap with no reader, and a `/tmp` pool 5 days from deletion

## Scheduling

- Cron-style or manual followup command that compares `next_followup` timestamps.
- Only advance step if `status` is still `sent` and `stop_if` conditions are not met.
- Log status changes per contact back to manifest.

## Anti-patterns

- Do not retry the same submit action without changing at least one condition: text, auth, or submit method.
- Do not loop on CDP when browser vision/snapshot keeps timing out after one fallback attempt.
- Do not treat loading screens, QR screens, and logged-in screens as interchangeable states.
- Do not hardcode absolute browser paths without fallback if profile loading fails.
- Do not declare posting failed solely from `is_posted=false` while the destination page URL indicates a successful submit.
- Do not loop on privilege escalation in locked containers.
- Do not report a capability as broken from a selector that matched nothing.
  Enumerate roles / `aria-label`s / `data-testid`s / leaf text and show the
  output first — several X controls are `aria-label`-only and will never match a
  testid search.
- Do not declare a failure off one empty view. A post that missed the community
  feed may be live on the author's profile with a valid permalink; check the
  source before reporting a negative.
- Do not read a page rendering zero items as an empty dataset when it rendered
  items minutes earlier — that is a render failure, so re-navigate and say so.
- Do not flush a posting backlog in one run when the plan is a spread-out
  schedule. Post one slot, keep a 90-min floor read from the live DOM, and let
  a missed window be missed.
- Do not report an unreadable analytics value as zero engagement. Premium gates
  impressions and reach; `None` is unmeasurable, not absent.
- Do not call rotating a prewritten post pool "research". Gate posting on a
  fresh research pass and let it halt, or admit the loop is writing blind.
- Do not log engagement without timestamps and a `type`, or the channel
  becomes unaggregatable and undashboard-able the moment you need a number.
- Do not follow in bulk to hit an engagement number; cap follow probability
  and skip existing follows.
- Do not add `Requires=` to a systemd timer that also targets the same
  service, and do not mix `08` with `08:30` in one `OnCalendar`.
- Do not guard a send's state write on a key the pool does not have
  (`if p.get("id")` over scraped records). The invite goes out, the row does
  not exist, cooldown does not apply, and the send log still says `SENT`.
- Do not report pool capacity from the write-back table. The DB records what
  has been touched; the worklist file is what you could send. Reading the
  first as the second understates capacity by an order of magnitude.
- Do not trust a sender's own `SENT` log as confirmation. Confirm against the
  independent state table, or a correct run and a broken run look identical.
- Do not extract a post id from page **text** when it only exists in an `href`
  attribute, and do not take "any `/status/` link" — filter on our own handle
  and take the first, since quoted posts and `/analytics` share that pattern.
- Do not trust a backfill that matched on a short text prefix, and do not act on
  a verifier's negative without reading what the verifier actually saw. An empty
  comparison means the probe failed, not that the data is wrong.
- Do not chase a missing row into the data path before sweeping the renderer's
  limit; newest-first truncation hides old rows with no error at all.
- Do not render a channel's health from a remembered value. Probe it in the same
  command, and keep "service reachable" separate from "account usable".
- Do not treat a user's "stop commenting" as a probability to lower. Delete the
  emission path and add a check that fails if it returns; a flag or a chance
  value is an invitation for the next run to re-enable it.
- Do not ship a canned template bank whose reachable-output count is small, and
  do not call `random.choice()` over it variety. Count distinct shapes after
  masking the variable slot before the loop ever runs.
- Do not splice a token scraped from someone else's post into a template
  (`f"... especially around {token}."`). The token was never checked for fit, so
  it will land as a person's name inside your sentence.
- Do not emit an action without logging its exact payload. A log with only
  `{type, target}` cannot be audited after the user objects, so the blast radius
  stays unknown.
- Do not thin research to a handful of unsourceable fragments. Every angle needs
  a permalink, and a gate that yields three unverifiable items will get bypassed.
- Do not hard-index optional fields in a scorer; rows from an older run lack the
  newer flags and the crash reads as "research is broken".
- Do not run a third-party automation driver on a debugging port something else
  already holds. A port check is not an identity check.
- Do not strip a posting path with a `continue` when a live block follows it; the
  block becomes unreachable-but-present and its own side effects silently stop.
  Delete it, then `ast.parse` and re-run the checker.
- Do not treat `disable --now` as "the automation is stopped." A `oneshot`
  already running keeps running, and if it carries `--send` it is still writing
  to a third party. `pgrep` the scripts, kill by pid, and remove the stale lock.
- Do not report a stop as clean when a unit came back `failed` — that is what a
  mid-run SIGTERM looks like. Overclaiming the stop is as false as overclaiming
  the send.
- Do not diagnose repeated posts from the picker without checking the tracker.
  Within-run selection was provably clean; the tracker never resets. Check
  `available >= slots` and how many picks are already used.
- Do not refill a schedule from the whole pool when the unique set is short.
  That converts a "too few posts" problem into a "same post again" problem.
- Do not act on a cheap proxy metric without validating it against the thing it
  claims to measure. An 8x8 colour-distance scan flagged 58 of 253 generated
  images as "near-identical"; inspecting the worst pair showed a paper plane vs
  an hourglass — different subjects sharing one dark palette. Metric said
  duplicate, reality said brand consistency, and I nearly reported a non-bug as
  a defect. Open the two extreme examples before concluding anything from a
  distance metric.

## Safety

- Respect platform TOS and anti-spam limits.
- Stop on first error surface unless explicitly told to retry.
- Never store secrets in manifest; reference external secret files.

## Templates

- `templates/whatsapp-outreach-manifest.json`
- `templates/whatsapp-intro.md`
- `templates/whatsapp-followup_1.md`
- `templates/whatsapp-followup_2.md`
- `templates/whatsapp-optout.md`
- `templates/x-post-text.js`
- `templates/x-post-image.js`

## Scripts

- `scripts/forbidden_path_check.py` — fails when a user-forbidden code path
  reappears (commenting, and any future standing prohibition); strips docstrings
  before matching so it cannot be defeated by its own documentation
- `scripts/x_growth_loop.py` — research-gated tick: refresh research if stale,
  build randomized slots, refuse a post inside the spacing floor, post one,
  confirm against the profile, then run the engagement pass
- `scripts/x_dashboard.py` — read-only multi-channel dashboard from the state
  ledger, engagement log and DB; flags stale research and unavailable metrics
- `scripts/wa_engine.js` — campaign send/followup/status commands
- `scripts/dashboard_server.js` — Node HTTP server for dashboard
- `scripts/post_x_verified.js` — Playwright X text post
- `scripts/post_x_image.js` — Playwright X text+image post
- `scripts/x_pacing_floor.py` — read the live post age off the profile and
  refuse a post inside the floor; `--engage` prints the recent-post table and
  flags Premium-gated metrics as unmeasurable rather than zero

## References

- `references/tick-ledger-and-observability.md` — per-run JSONL ledger so "when
  did it run and what did it do" is answerable; the record-inside-the-lock
  placement bug, outcome vocabulary, reading real counts back, and serving the
  dashboard over HTTP by reusing the CLI's renderers
- `references/post-permalinks-and-false-negatives.md` — why a post-confirm step
  silently stored `status: null` for every post (id lives in the `href`, not the
  text), the prefix-match backfill that attached wrong URLs, the verifier that
  reported false `MISMATCH` by comparing against an empty list, the limit sweep
  that proved rows were merely truncated, and the measured proof that LinkedIn
  exposes no post permalink in the feed DOM
- `references/connection-request-tracking.md` — why a sender can log `SENT`
  for every invite and write nothing to the DB: the scraped pool has no `id`,
  so `if p.get("id")` is dead code; the `mark_url` upsert, the backfill, and
  why the pool and the DB must never be conflated
- `references/canned-template-bank-spray.md` — how a 6x8 canned reply bank
  produced 101 visible-repeat replies across 76 handles, the shape-counting audit
  that detects this class of bug, clean removal of an emission path without
  orphaning its helpers, and the same disease found in the post pool
- `references/post-pool-rotation.md` — why "same post daily" was not a picker
  bug: within-run selection was provably clean at every exhaustion level, and the
  real cause was an append-only tracker nothing resets (8 of tomorrow's 10 picks
  already used). Includes the availability check that catches it, why refilling
  from the whole pool is the wrong trade when the complaint is duplicates, and
  the date-relative pitfall where `--plan` only ever produces today
- `references/stopping-outreach-teardown.md` — why `systemctl disable --now` does
  not stop outreach: two `--send` services were mid-run, they dropped a stale
  `.cdp.lock`, and the daily-report cron would still have described automation
  that no longer ran
- `references/browser-profile-isolation.md` — pre-flight for installing
  third-party browser automation: a port check is not an identity check, how to
  give a new driver its own port and profile, and how to confirm isolation in the
  process table
- `references/x-post-workarounds.md` — browsers tried, failures, and working method
- `references/dashboard-tunneling.md` — tunneling options, plus measured
  cloudflared quick-tunnel traps (fused host+path URLs, duplicate tunnels on one
  port, launcher-exits-vs-tunnel-alive, self-matching `pkill`) and the
  htpasswd-recovery procedure with its three-way verification
- `references/dashboard-tunneling-fixes.md`
- `references/openwa-evaluation.md` — OpenWA repo review, ban-risk notes, deployment constraints
- `references/dashboard-audit-2026-08-01.md` — audit findings and fixes applied
- `references/oracle-deployment.md` — Oracle Free Tier constraints, disk/inode hygiene, Hermes install notes
