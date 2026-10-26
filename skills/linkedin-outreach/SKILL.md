---
name: linkedin-outreach
description: LinkedIn outreach automation via browser automation.
version: 1.0.0
tags: [linkedin, outreach, automation, camofox, chrome-cdp, connection-requests, messaging, posts]
---

# LinkedIn Outreach Automation

Use this skill when the user asks to:
- Send LinkedIn connection requests programmatically
- Send InMail or messages to LinkedIn profiles
- Post to LinkedIn feed via automation
- Run LinkedIn outreach campaigns (sequences, templates, scheduling)
- Debug LinkedIn automation failures

## Platform realities

### Anti-bot escalation — full-domain blocking (2026-08-21)

LinkedIn's anti-bot detection now blocks automated browser fingerprints at multiple levels simultaneously, regardless of cookie state. Three distinct symptoms were observed in a single session, all server-side blocks:

**Symptom 1: `NS_ERROR_NET_EMPTY_RESPONSE`** — network-level connection drop on `/feed/` and `/in/<profile>/`. LinkedIn drops the connection entirely rather than returning a page.

**Symptom 2: `NS_ERROR_REDIRECT_LOOP`** — Firefox redirect loop detection on homepage (`/`). Firefox error page: "The page isn't redirecting properly", "Camoufox can't connect to the server at www.linkedin.com". Earlier in the session the homepage loaded (redirecting to `hp`), but escalated to full redirect loop.

**Symptom 3: "Problem loading page" with empty DOM** — profile pages (`/in/<profile>/`) render a Firefox error page. `document.title` = "Problem loading page", `document.body.innerText` = `""`, `document.querySelectorAll("button")` = `[]`. URL still shows the profile URL. Clicking "Try Again" does not break the loop.

**What does NOT work:**
- Cookie import alone (any browser backend, any cookie set) — produces blocked/empty pages, NOT working sessions
- Clicking "Try Again" on "Problem loading page" — re-blocks immediately
- Multiple retries of the same blocked approach
- Different `userId` / `sessionKey` — same behavior
- Waiting and retrying

**Verification method (page-state evidence, NOT HTTP status):**
- `document.title` — if "Problem loading page", blocked
- `document.body.innerText` — if empty, blocked
- `document.querySelectorAll("button")` — if `[]`, no interactive elements
- URL — if `/login` or `/signin`, not authenticated
- HTTP 200 alone does NOT confirm a working session

**What works:**
- **Option A (VERIFIED 2026-09-28)**: Real Google Chrome + CDP with `li_at` cookie.
  Full authenticated feed rendered — global nav, notification badges, post
  composer, own profile card. This is the path that works. See
  "Chrome + CDP is the only working backend" below.
- **Option B**: LinkedIn Official API (requires Developer account, OAuth, approval)
- **Option C**: VNC manual login (avoids ever handling the cookie, but the
  session is identical once established)

### Chrome + CDP is the only working backend

Cookies alone are NOT the problem — the browser is. Measured on this box:

| Backend | Result |
|---|---|
| Camofox Firefox (any cookie method) | blocked, 4 methods tried |
| Playwright bundled Chromium + `li_at` | blocked |
| **real `/usr/bin/google-chrome` + CDP + `li_at`** | **full feed renders** |

LinkedIn fingerprints headless Firefox and Playwright's Chromium but passes
genuine Chrome. Use the system binary, never the Playwright-downloaded one.

```bash
/usr/bin/google-chrome --remote-debugging-port=9222 \
  --no-first-run --no-default-browser-check \
  --user-data-dir=/path/to/dedicated/profile \
  --headless=new --disable-gpu --disable-dev-shm-usage \
  --disable-background-networking --disable-sync about:blank
```
Then `chromium.connect_over_cdp("http://127.0.0.1:9222")` and
`context.add_cookies([...])` with `domain: ".linkedin.com"`, `secure: true`.
Cookies sourced from a pasted cookie header work — parse on `;` then first `=`.

### Verified working path (2026-09-28) — desktop Chrome, user logs in once

The reliable setup, proven on this box:

```bash
/home/opc/bin/remote-desktop    # Xvnc :1 + Chrome + websockify (systemd unit)
/home/opc/bin/vnc-tunnel        # cloudflared quick tunnel -> public noVNC URL
```

- Chrome runs on `:1` with `--remote-debugging-port=9222`, profile
  `/home/opc/.li-chrome-profile`, and `--password-store=basic
  --use-mock-keychain` (otherwise a GNOME keyring modal blocks the page).
- The **user** types the password in the noVNC browser. The agent never sees
  it, and no token is ever pasted into a transcript.
- Attach with `p.chromium.connect_over_cdp("http://127.0.0.1:9222")` and reuse
  `browser.contexts[0].pages[0]`. Do NOT open a new context or inject cookies.

Measured results:

| Test | Cookie session | Desktop session |
|---|---|---|
| First load | full feed | full feed |
| Repeat loads | **0/6** | **5/5** |
| After 300s cooldown | still failing | n/a |
| Identity | Kunal Sharma | Kunal Sharma |

The cookie session worked exactly once and never again — a burned token. The
desktop session survives repeated navigation across feed, network,
notifications and messaging. This is why the manual login is not a fallback,
it is the correct path.

## Scraping LinkedIn search results (people)

**LinkedIn has hashed every CSS class to an opaque token** — the live DOM
returns `m6f2z`, `m6fa1p`, `m6fbwq`, etc. Any selector built on
`[class*=headline]` or `[class*=entity-result]` finds nothing. Verified by
dumping `card.querySelectorAll('*')` classNames: 60+ classes, all `m6*`.

**What does work: the name anchor's own `innerText`.** For a person card it
carries name, connection degree, and the first slice of the headline:

```
'Lucky Saini • 2nd\n\nFounder | Custom Printed Tissue Paper Manufacturer | ...'
```

Build one record per anchor so a name can never be paired with a different
person's URL. Walking up N parents to find a container does not work — the
whole results column is one ancestor, so names end up beside their
neighbours' URLs. That caused 42/43 malformed rows before the fix.

```python
page.evaluate("""() => {
    const out = [], seen = new Set();
    for (const a of document.querySelectorAll('a[href*="/in/"]')) {
        const href = a.href.split('?')[0].replace(/\\/$/, '');
        if (!href || seen.has(href)) continue;
        const raw = (a.innerText || '').trim();
        if (!raw) continue;                       // photo/action anchors
        if (/^(connect|follow|message|view)$/i.test(raw)) continue;
        seen.add(href);
        out.push({url: href, raw: raw});
    }
    return out;
}""")
```

`a.href` is already absolute — do not prepend the domain. Name is
`DEGREE.split(first)[0]` where `DEGREE = /[•·]\s*\d+(st|nd|rd|th)\+/`.
Headline is the next non-empty line; strip a trailing `...` (LinkedIn truncates).

## Keyword search returns the wrong audience — verify ICP before outreach

`saas founder delhi` / `b2b saas delhi` on people-search returned 14
founder-matching profiles, and **11 of 14 were off-ICP**: tissue-paper
manufacturers, car rentals, D2C streetwear, gym brands, interior fit-outs.
Only ~3 were genuinely software-adjacent (B2B SaaS SDR, RevOps/automation).

LinkedIn people-search matches loosely on the word "founder" and ignores the
industry qualifier. Keyword filtering is not targeting. Prefer signals that
cannot be faked: a hiring post, a company page's "people also viewed", or
matching against a real company list. State the off-ICP rate to the user
instead of presenting a founder-heavy list as a good one.

## Sending a connection request — the verified DOM path (2026-09-29)

Three selector guesses failed before the live DOM was dumped. The correct
elements, measured:

**1. The Connect control's accessible name is NOT "Connect".**

```
[aria-label="Invite Shubham Jain to connect"]   href="/preload/custom-invite/"
```

There is no `h1` on a current public profile — the name is in `h2`. Use
`document.title` (`"Aditya Poddar | LinkedIn"`) as the identity check instead.

**2. The link click does nothing; the profile's own `href` works.**

`inv.click()` produced no dialog at all. Navigating to
`https://www.linkedin.com/in/<vanity>/preload/custom-invite/` does. Do not
scroll to the nav-dup link — it is covered by the "For Business" menu and
gets intercepted.

**3. The note field is a `<textarea>`, not a contenteditable, and it is not the
only one on the page.**

```html
<textarea class="connect-button__send-invite" rows="2"
          placeholder="Ex: We know each other from…">
```

The messaging compose box (`.msg-form__contenteditable`, aria-label "Write a
message…") is **also inside a `[role="dialog"]`**. A dialog-scoped selector
matches the wrong box and fires a real DM. Target the class, and verify the
field's value before sending.

**4. Send must be scoped to the invite dialog only.**

The messaging overlay has its own `Send` button. Match on
`[role="dialog"] button:has-text("Send")` *and* reject any dialog whose text
lacks "invitation".

### Hard limits read from the live dialog

- **"N personalized invitations remaining for this month"** — free accounts
  get **3 per month**, not per day. This is a monthly quota, not a rate limit.
  It cannot be raised by pacing. Premium is the only lever.
- The dialog text says "limit personal note to 300 characters" but the live
  counter reads `0/200` and the textarea enforces **200**. Assert 200.
- At zero the dialog replaces the note field with a paywall:
  **"You're out of free custom notes. Bypass the limit with Premium."**

### Enforcing cooldown is a code concern, not a config one

`in_cooldown()` returns **False** when `cooldown_days` is missing — it does not
raise. A channel with no cooldown key therefore re-contacts everyone on every
run, silently. Assert that every channel in `LIMITS` has `cooldown_days`;
do not rely on remembering to set it. This bit once: LinkedIn had no cooldown
key, so all 30 invites were eligible for immediate re-send.

Also: a sender that reads its worklist from **JSON, not the DB**, bypasses the
cooldown entirely no matter what the config says. Filter the batch against the
DB before sending.

The same JSON-driven sender has a second, quieter half to the same bug: the
people in the JSON have no `id`, so the `mark(id, "sent")` call is skipped and
**nothing is ever written to the DB**. A 30-invite run left `people` with zero
rows touched, which meant the cooldown had nothing to protect even after the
missing key was fixed. Whenever a sender's worklist comes from a file, either
give it DB ids or reconcile afterwards, and check the row count — a send log
that says "sent" while the DB is empty is a false success.

**This one was still live after the cooldown fix.** Measured 2026-10-01: the
worklist is `/tmp/li_pool.json` (scraped, 204 records, no `id` key at all), so
`if p.get("id")` was dead code and three confirmed `SENT` invites produced
**zero** rows. Fix by upserting on the profile URL — the key the cooldown query
already uses — and backfill the sends made while the write was broken, or those
people stay immediately re-invitable. Confirm with
`select ... from people where date(datetime(touched_at,'+5 hours','utc'))=today`,
never with the sender's own log. Full recipe:
`outreach-automation` → `references/connection-request-tracking.md`.

Do not read the `people` table as the prospect pool. It is a write-back log of
what has been touched; the JSON worklist is the inventory. Confusing them
understated the pool as 1 eligible when 171 were.

Read the allowance from the dialog at send time and stop at 0 — never infer it
from a local config value, which will silently contradict the platform.

### The 3/month quota is for NOTES ONLY — the no-note path is a different budget

This is the single most useful thing to know before telling a user they are
capped. The allowance is **personalized** invitations. The dialog's other
button, **"Send without a note"**, bypasses the note field entirely and is
therefore **not** subject to the 3/month quota:

```python
# Distinct budgets — never count them as one
if note is None:
    click("Send without a note")     # separate, much larger weekly cap
else:
    read_allowance(); if 0: stop     # 3/month on free tier
    click("Add a note"); type; verify
```

Verified: with the note allowance exhausted at 0, the no-note path still sent
and still showed as pending on the target's profile.

So the honest answer to "the quota is spent" is **not** "you are done" — it is
"notes are done; un-noted invites still work, at a materially lower accept
rate." Say that instead of reporting a dead end.

**Tradeoff to state, not hide:** no-note invites are accepted far less often.
LinkedIn itself pushes the note, and on a real run *both* replies came from
people who had received a personalized note. Volume of blank invites off a
young account spends the follow-up you cannot replace. Offer the choice.

### Both invite URL forms exist; prefer the root one

`/in/<vanity>/preload/custom-invite/` and the root
`https://www.linkedin.com/preload/custom-invite/?vanityName=<vanity>` both
render the dialog, but the `/in/` form intermittently returns a **blank page**
(empty `document.title`, zero dialogs) on profiles that render fine a moment
later. When the dialog does not appear, retry once on the root form before
concluding anything about the person.

### A blank profile page is not proof of a block

An empty `document.title` with zero dialogs looks identical to a LinkedIn
block. It was not: the feed, the message overlay, and other profiles in the
same tab all rendered normally, and the same profile URL later worked. Confirm
with one of those before concluding the account is restricted, and before
aborting a run.

### Confirming a send actually happened

A closing dialog is not proof. Two independent signals:

1. The allowance counter drops (`3 → 2 → 1 → 0`).
2. Reload the profile: an invite-sent person has **no** `[aria-label*="to
   connect"]` for themselves. Always include an unsent profile as a control, or
   a page-render failure looks identical to a pending invite.

`/mynetwork/invitations/` is **not** the Sent page; it 404s. The Sent list is
under My Network, reached by clicking, not by URL.

Inbound replies surface as `[role="dialog"]` message popups on unrelated pages
(the "For Business" dropdown reuses the dialog role). Scanning all dialogs for
`sent the following messages` is a cheap way to discover who replied — and on
this run it surfaced two people asking real questions, which was worth more
than the invites that produced them. Check the inbox before spending the day's
send budget.

## Reading the messaging inbox (verified 2026-09-30)

**Conversation rows contain NO anchor.** A row is
`li.ember-view.scaffold-layout__list-item.msg-conversation-list`, and inside it
the only element with an href or a useful label is
`button.msg-thread-actions__control`. Measured: `anchors: []` for every row.
So `li a[href*="/messaging/"]` returns nothing and any href-harvesting loop
silently yields `{}`.

**Do not harvest thread URLs. Click by coordinates.**

```python
box = pg.evaluate("""(nm)=>{
  const li=[...document.querySelectorAll('li')]
    .find(e=>(e.innerText||'').includes(nm));
  if(!li) return null;
  li.scrollIntoView({block:'center'});
  const r=li.getBoundingClientRect();
  return {x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2)};
}""", name)
pg.mouse.click(box["x"], box["y"])
```

`scrollIntoView` matters: rows below the fold resolve to a y outside the
viewport and the click lands on whatever is actually there.

### The trap that will hand you another person's conversation

`items[0].querySelector('button, a, [role="button"]').click()` **does not
throw, returns true, and opens nothing.** The thread pane then still holds
whatever conversation was open previously, and a plain
`querySelectorAll('li')` read returns that stale thread's messages under the
target's name.

Observed exactly this: asked for Agnivesh Sharma's thread, got Vikas babu's
conference invite printed under her heading. Nothing in the return value says
"wrong". Two guards, both required:

1. Click by coordinates, not by `element.click()` on a child.
2. Assert the opened thread matches the intended person — the URL moves to
   `/messaging/thread/<base64>/`, and the header in the thread pane must contain
   the name. Re-read the pane *after* confirming the header, never before.

### Do not filter conversation rows by anchor presence

`li:has(a[href*="/messaging/"])` matched exactly one element — the `Messaging`
nav item — which reads as "the inbox is empty". Dumping
`[...document.querySelectorAll('li')]` innerText instead surfaced ten real
conversations with names, dates and last-message previews in one call. That
filter is the reason to distrust any "inbox looks empty" conclusion.

Noise to strip from thread dumps: `Press return to go to conversation
details`, `Status is online/reachable`, `Reply to conversation with`,
`Conversation List`, `screen reader users`, `Business Services`, `Get the
LinkedIn app`.

Full recipe: `references/linkedin-messaging-inbox.md`.

## Reply drafts need the user's facts, not the agent's

When a vendor or prospect asks a real business question ("how are your clients
coming in?", "are you still handling follow-ups manually?"), the answer must
come from the user. `config.py` ships `OFFER = ""` and `PROOF = ""`
deliberately empty for this reason — a placeholder sent to a real person is
spam that costs a connection.

Read the thread, then ask the user the specific questions the thread implies
and draft from their answers. Do not invent a pipeline story. A non-answer
("I'm not sure") already went out once in this account and reads as a
soft brush-off to anyone selling against it.

## Report counts and engagement; do not just act

This user asks for the numbers — "how much did you post and what about
engagement" — and wants a dashboard to track every channel without asking.
Ship a readable status view (`--live` for measured reads, `--week` for trend)
that distinguishes **confirmed**, **dispatched-unconfirmed**, and
**unmeasurable-because-Premium-gated**. Never render an unavailable metric as
`0`.

## Rules for using the attached session
- Reuse the existing tab. A burst of fresh navigations reads as bot behaviour.
- Pace it: 10-15s between page loads.
- Verify by page state (`My Network` / `Start a post` present, `Sign in` /
  `authwall` absent) and by screenshot. Never by HTTP status.
- Check liveness before any run rather than assuming the session persisted.
- `remote-desktop.service` is enabled; the tunnel hostname changes on restart,
  so re-read `/tmp/vnc-tunnel.log` instead of reusing an old URL.


**Decision tree:**
```
Need LinkedIn automation?
├── Can user manually log in to Camofox once?
│   └── YES → Manual login, reuse profile, then run scripts
├── Is LinkedIn API access available?
│   └── YES → Use official API
└── NO to both
    └── LinkedIn automation is NOT currently possible
        → Focus on working channels (WhatsApp, X, etc.)
```

### Verified failure mode

```
Navigating to https://www.linkedin.com/feed/:
  NS_ERROR_NET_EMPTY_RESPONSE
  Call log: navigating to "https://www.linkedin.com/feed/", waiting until "domcontentloaded"

On homepage (https://www.linkedin.com/):
  Redirects to https://www.linkedin.com/hp (logged out)
  Snapshot shows "Sign in" / "Agree & Join LinkedIn"
```

Cookie import response:
```
POST /sessions/linkedin_main/cookies  →  {"ok":true,"userId":"linkedin_main","count":24}
```
But subsequent tab creation shows login page — cookies not applied to browser context.

## Working alternatives

### Option A: Chrome CDP with existing LinkedIn session

If a Chrome/Chromium profile has an active LinkedIn session (cookies in `Default/Cookies` SQLite database), use Chrome CDP directly. LinkedIn treats Chrome as a normal browser and won't block it.

**Preconditions:**
- Chrome/Chromium installed (`which google-chrome` → `/usr/bin/google-chrome` in this env)
- Chrome profile with LinkedIn cookies exists
- CDP port reachable (launch Chrome with `--remote-debugging-port=9222`)

**Launch:**
```bash
google-chrome --remote-debugging-port=9222 \
  --no-first-run --no-default-browser-check \
  --user-data-dir=/path/to/chrome-profile \
  --headless=new --disable-gpu --disable-dev-shm-usage \
  --disable-background-networking --disable-sync
```

**Verify CDP:**
```bash
curl http://localhost:9222/json/list  # should return tabs
```

**Navigate to LinkedIn:**
Use CDP commands or Playwright with the Chrome profile.

### Option B: Playwright Chromium + cookie import

Import LinkedIn cookies into a Playwright Chromium context. This is the verified path from `browser-social-composer` for X — same pattern works for LinkedIn.

```javascript
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const cookies = JSON.parse(fs.readFileSync('linkedin-cookies.json', 'utf8'));
await context.addCookies(cookies);
const page = await context.newPage();
await page.goto('https://www.linkedin.com/feed/');
// Verify not on login page
```

**Caveat:** LinkedIn may still detect headless Chromium. Use a real Chrome user agent and non-headless if possible.

## What doesn't work

| Approach | Result |
|---|---|
| Camofox Firefox + cookie import (REST API) | Login page, NS_ERROR_NET_EMPTY_RESPONSE on feed |
| Camofox Firefox + cookie import (via newContext.addCookies) | Same — cookies accepted but session invalid |
| Camofox Firefox direct navigation to `/feed/` | NS_ERROR_NET_EMPTY_RESPONSE |
| Camofox Firefox direct navigation to `/in/<profile>/` | NS_ERROR_NET_EMPTY_RESPONSE |

## Template system

Templates for LinkedIn outreach messages and posts. Supports variable substitution with `{{variable}}` syntax.

**Template types:**
- `connection` — connection request notes (limit: 300 chars)
- `message` — InMail / direct messages (post-connection)
- `post` — feed posts (limit: 3000 chars)

**Available templates:**
- `connection-cold` — first connection request (variants: default, short, professional)
- `connection-warm` — after engaging with content (variants: default, event)
- `followup-after-connect` — post-connection follow-up (variants: default, brief, soft)
- `cold-outreach` — direct value proposition (variants: value_first, question_based, short_pitch)
- `event-followup` — after meeting at conference (variants: default, no_resource)
- `engagement-to-dm` — after engaging with post (variants: default, short)
- `referral-request` — ask for referral/intro (variants: direct, soft)
- `reengagement` — re-contact dormant lead (variants: default, update_only)
- `thank-you` — appreciation (variants: default, brief)
- `post-thought-leadership` — insight post (variants: story, contrarian, how_to, lesson_learned)
- `post-announcement` — company/product news (variants: launch, milestone)
- `post-engagement` — conversation starter (variants: poll_style, debate, ask_experts)

**Render a template:**
```bash
node linkedin_templates.js render connection-cold --variant short --firstName "Sarah" --company "Acme" --role "CTO"
```

## Campaign engine structure

The campaign engine orchestrates LinkedIn actions with templates, targets, rate limiting, and state tracking.

**Actions supported:**
- `post` — post to LinkedIn feed
- `connect` — send connection request (with optional note)
- `message` — send InMail/message (requires existing connection)

**Campaign config:**
```json
{
  "name": "Outreach to CTOs",
  "actions": [
    {"type": "connect", "note": "Hi {{firstName}}..."},
    {"type": "message", "message": "Thanks for connecting..."}
  ],
  "targets": [
    {"profileUrl": "https://linkedin.com/in/person1", "firstName": "John"}
  ],
  "rateLimitMs": 30000,
  "dryRun": false
}
```

**Run:**
```bash
node linkedin_campaign.js campaign --config campaign.json
```

**State tracking:** Actions are logged to `linkedin-campaign-state.json` with timestamps, success/failure, and targets. History is queryable via `node linkedin_campaign.js status`.

## Rate limiting

LinkedIn enforces strict rate limits on connection requests and messages. Default campaign rate limit is 30s between actions. Do not reduce this without testing. Connection request limits are particularly tight — exceeding them risks account restriction.

## Verification

After any LinkedIn action, verify with:
1. **URL check** — not on `/login` or `/signin`
2. **Snapshot** — page content confirms expected state
3. **Screenshot** — visual proof saved to `/tmp/linkedin-<action>-<timestamp>.png`

Do not declare success from HTTP status alone. LinkedIn can return 200 on login page.

## Script debugging guide

See `references/linkedin-invite-allowance-and-verification.md` for the measured
invite-allowance numbers, the six selector attempts that failed, the working
selector chain, the control-based send verification, and the `random` traps in
a human-pacing layer.

See `references/linkedin-script-debugging.md` for:
- Diagnostic probe script template (standalone tab + navigate + snapshot + button find)
- Missing `log()` function fix
- Embedded null bytes in script files — diagnosis and cleaning
- Playwright pseudo-selectors (`:has-text()`, `:contains()`) do NOT work in Camofox Firefox — replace with `querySelectorAll` + text content matching
- Snapshot return value: return `res` not `res.snapshot`
- Cookie import must be called in the main flow before `createTab()`, not just defined
- Default tab URL must be `https://www.linkedin.com/`, not `about:blank`

## Anti-bot failure modes

LinkedIn blocks automated browser profiles at the network/server level. Two manifestations observed:

1. **`NS_ERROR_NET_EMPTY_RESPONSE`** on `/feed/` and `/in/<profile>/` — network-level connection drop. See `references/linkedin-anti-bot-redirect-loop.md` for full analysis.
2. **"The page isn't redirecting properly"** on profile URLs — Firefox redirect loop detection. Same root cause (browser fingerprint blocked), different symptom. Clicking "Try Again" does not break the loop.

Cookie import via REST API accepts cookies but does not produce an authenticated session. The only verified working approach is manual login in a visible Camofox browser.

## Cross-channel notes (siblings are user-owned — recorded here)

- `x-outreach` — X DM outreach. Its free DM ceiling (~20/day) is an
  **unverified prior**, not a measurement: X shows no allowance in the UI the
  way LinkedIn prints an invite counter, so the real number has to be read off a
  live rate-limit response. Establish it before quoting a figure.
- `client-acquisition` — cross-channel ramped caps, proof-before-batch,
  control-based verification, and replies-over-sends.
- `cold-outreach-pipeline` — queue/cooldown/clock-seam build order.

The transferable rule, and the one that cost a day here: **an exhausted quota
on one route is not a dead channel.** LinkedIn splits 3 personalized notes per
month away from a separate no-note budget; check for the equivalent split
before reporting a channel as finished, and state the accept-rate tradeoff
rather than presenting a false either/or.

## Verify SPA actions on the network, not the DOM (measured 2026-09-30)

A **working action plus a wrong verifier reads exactly like a broken action.**
On LinkedIn feed comments this produced four false "failed" reports in one
session, then a feature wrongly disabled and reported to the user as
"unproven".

The comment submit POSTs to:

```
.../flagship-web/rsc-action/actions/server-request?sduiid=com.linkedin.sdui.comments.createComment
```

and returns **HTTP 200**. That is the only trustworthy control.

Every DOM check reported failure on comments that had actually published:

- `document.body.innerText` not containing the text after submit
- text absent from `/in/<user>/recent-activity/comments/`
- `[contenteditable="true"]` still mounted rather than cleared
- `"Submitting comment"` in body text — present in BOTH success and failure, so
  the spinner discriminates nothing

```python
s.send("Network.enable")
try:                      # drain stale events so the read is only about THIS action
    s.ws.settimeout(0.4)
    while True: s.ws.recv()
except Exception: pass
s.ws.settimeout(1.0)
# ...perform the click...
end = time.time() + 20
while time.time() < end:
    try: m = json.loads(s.ws.recv())
    except Exception: continue
    if m.get("method") == "Network.responseReceived":
        r = m["params"]["response"]
        if "createComment" in r.get("url", ""):
            got_status = r.get("status"); break
```

`Network.getResponseBody` on that request returns `-32000 No data found for
resource with given identifier`. Harmless — the body is already consumed. Catch
and ignore; the status is all you need.

**Rule: when a check contradicts a plausible working path, capture the network
before concluding anything.** Never disable a feature because a DOM read could
not see it.

Controls that DO work on LinkedIn:

| action | control |
|---|---|
| feed like | reaction label flips off `no reaction` |
| feed comment | HTTP 200 on `createComment` |
| DM | text present in thread AND composer cleared |

DM send detail: **Enter does not send** — it leaves text staged. Click
`.msg-form__send-button` (disabled until the composer has text).

Full selector map, the ProseMirror typing trap, and the network transcript:
`references/linkedin-feed-engagement-dom-2026-09-30.md`.

Lazy-loading the feed: `window` is **not** the scroller (`document.body` is
`overflow: hidden`, `scrollHeight 793`); the real one is `MAIN`
(`overflow-y: scroll`). Real wheel events work, but
`Input.dispatchMouseEvent` **returns no reply until `Input.enable` is sent
first**, so `send()` hangs the socket until timeout. When scrolling stops,
check `scrollTop == scrollHeight - clientHeight` before assuming the automation
broke — it may be the true bottom.

## You cannot rank posts from the feed — it renders no engagement numbers

Measured 2026-10-03. Every reaction button on `/feed/` reads
`Reaction button state: no reaction`; **0 of 3 posts** exposed a reaction,
comment, or view count. Together with the missing permalink, that means **a
LinkedIn feed cannot be ranked by performance from the feed itself.** Any
"what works on LinkedIn" sourced from feed scraping is fabricated.

Own-side analytics **do** render, at
`/in/<handle>/recent-activity/all/` — impressions, reactions, comments per post.
Read live: `116 impressions / 3 reactions / 2 comments`, then 97, 48, 46, 48.
That page has a **different DOM shape** (zero `<p>` elements, container
`innerText` instead), so an extractor validated on the feed finds nothing
there.

Read the handle off the live page, never guess: `kunal-sharma-9aa97312` is a
**404**; `kunalsharmaai` renders. Identity-link `href`s come back **absolute**
— do not prepend the host.

Full selectors, the URL traps, and the 3-post structural census (with the
`n=3` caveat): `references/post-analytics-and-impressions.md`.

## Off-by-page-context: always navigate after attaching

A script that attaches to "whatever tab is open" reads the wrong page and
reports an empty feed — one run logged a halt because a prior probe had left
the browser on the comments tab. Always `goto()` the target route explicitly
after attaching, before counting anything.

## Check every channel's liveness, not just the one being worked on

Three consecutive scheduled X ticks had failed silently while LinkedIn work
proceeded and was reported as the current task. The user had to ask what
happened to X. A per-channel "last successful run" read from the run log is the
cheapest guard against reporting a working channel while another is dead.

## Related skills

Feed likes/comments selectors and the raw-CDP driver are in
`references/linkedin-feed-engagement-dom-2026-09-30.md` (and the
`linkedin-feed-engagement` skill, which is user-owned).

- `camofox-social-automation` — Camofox patterns, composer behavior, fallback rules
- `browser-social-composer` — Playwright cookie-backed posting fallback
- `outreach-automation` — campaign engine structure (WhatsApp + X focused)
- `x-social-poster` — X/Twitter posting via Camofox (pattern transfers to LinkedIn)
