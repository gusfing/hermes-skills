---
name: whatsapp-outreach-backends
description: |
  WhatsApp outreach backend fallback patterns and evaluations for Linux
  containers. Use when primary CDP fails, when Playwright direct is needed,
  or when evaluating gateway projects like OpenWA.
version: 1.0.0
tags: [whatsapp, outreach, fallback, playwright, camofox, openwa]
---

# WhatsApp Outreach Backends

## Fallback order

```
1. Local Chrome CDP (127.0.0.1:9222)
2. Playwright direct with UA override
3. Camofox
```

## 1. Local Chrome CDP

- Attach via Hermes: `/browser connect http://127.0.0.1:9222`
- Uses existing Chrome profile with WhatsApp already logged in
- Stable, fast, no additional server needed

### Caveat in containers
- `Target.getTargets` may work, but `Page.navigate`, `Runtime.evaluate`, `Page.enable` can time out
- If CDP page ops time out, fall back immediately to Playwright direct

## 2. Playwright direct with UA override

Use when CDP page ops time out.

### Chrome UA override is mandatory
WhatsApp Web rejects default Playwright/Headless UA. Always override:

```js
const context = await chromium.launchPersistentContext(profileDir, {
  executablePath: '/opt/data/.playwright/chromium-1234/chrome-linux64/chrome',
  args: ['--no-sandbox','--disable-gpu'],
  headless: true,
  userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'
});
```

### QR capture flow
```js
const page = await context.newPage();
await page.goto('https://web.whatsapp.com', { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(20000);
const qr = await page.$('canvas');
if (qr) await qr.screenshot({ path: '/opt/data/outreach/dashboard/public/qr.png' });
await context.close();
```

### Profile reuse
- Reuse same `--user-data-dir` to preserve login state
- First run: manual QR scan
- Subsequent runs: session persists

## 3. Camofox

- Use only when CDP and Playwright are unavailable
- Requires Camofox server on 127.0.0.1:9377
- Dedicated `userId` per account for isolation
- Reuse same `userId` + `sessionKey` to preserve chat history

### Known issue
- Keyboard events may not sync to React state in WhatsApp/X composers
- If typing doesn't register, stop and report rather than retrying

## OpenWA evaluation

### What it is
- Open-source WhatsApp API gateway (NestJS + TypeScript)
- Uses `whatsapp-web.js` or Baileys under the hood
- Docker-native, multi-session, dashboard UI
- Repo: https://github.com/rmyndharis/OpenWA

### Ban-risk profile
- `whatsapp-web.js` engine: lower risk, drives real headless Chromium
- `baileys` engine: higher risk, speaks protocol directly

### Safe-sending guidelines
- Warm up fresh numbers for several days before outreach
- Don't cold-blast strangers
- Rate-limit: few messages per minute per session
- Use opted-in recipients
- Keep SMS/email fallback for auth-critical flows
- Residential proxy helps; cheap datacenter IPs are flagged more

### When to use it
- When you need a full API gateway + dashboard + multi-session management
- When you can run Docker Compose in the environment
- Not recommended for lightweight single-account outreach

### When NOT to use it
- In containers without Docker Compose
- For simple one-off sends
- When resource usage matters (~300-500MB RAM per session)

## Driving OpenWA over REST

Full verified route table, auth header, DTO constraints, and the Redis
fail-open trap: **`references/openwa-rest-api.md`**

Load that before hand-writing curl against a gateway. The short version:

- Auth header is **`x-api-key`**. The intuitive alternatives (`api_key`,
  `Authorization: Bearer`) return 401 even when the value is correct, so
  prove the header with a 3-way test: no header -> 401, wrong value -> 401,
  real value -> 200.
- The SPA is mounted at `/`, so `/docs`, `/api-docs`, `/swagger` and
  friends all return `200` + HTML. A 200 proves nothing; check for a JSON
  body. Distinguish a real route from a wrong prefix by `401` vs `404`.
- **An unexplained bare 400 on a write route is a validation constraint, not
  a service fault.** NestJS DTOs survive compilation with their
  `class-validator` decorators readable in the image
  (`docker cp <c>:/app/dist /tmp/d`) — read them instead of guessing bodies.
- Redis-backed features (rate limiting) **fail open and log it**. Grep for
  `failing OPEN` / `ETIMEDOUT` before debugging a bare 400.
- A space in a session name is a 400. Generate `[a-z0-9-]` names.
- Create -> start -> fetch QR is fully automatable; the QR endpoint returns
  a base64 data URL, so decode and send the image rather than standing up a
  dashboard. **Scanning it is the human step** — surface it and stop.
  `GET /api/sessions` returning `[]` means no account is paired and no send
  route can work.

## Session `qr_ready` is the real blocker, not reachability

Measured 2026-10-01 after a dashboard claimed the channel was `unreachable` for a
whole day. It was reachable the entire time:

```
GET /api/health          → 200
127.0.0.1:2785           → LISTEN
docker ps                → openwa-api  Up 25 hours (healthy)
GET /api/sessions/<id>   → status qr_ready, phone None, connectedAt None
```

The gateway was healthy. The **session had never paired** — created
`2026-09-30T11:26:35Z`, still `qr_ready`, `phoneNumber: null`. A user reporting
"can't scan, try again later" is describing an unpaired session whose QR keeps
regenerating, not a broken service.

**Check the session status before diagnosing the gateway.** Three commands settle
it in one shot:

```bash
curl -s -o /dev/null -w "%{http_code}\n" --max-time 12 http://127.0.0.1:2785/api/health
ss -ltnp 2>/dev/null | grep 2785
# then the authoritative one — the session, not the port:
GET /api/sessions/<id>   → status / phoneNumber / connectedAt
```

Report these as **separate lines**. `API up` and `account usable` are different
facts, and collapsing them into one "unreachable" field is what made the day look
broken.

**Derive that field from a live probe, never from a stored value.** A status
line that is not a fresh call is a claim, and it rots silently. Ship the probe as
an importable module so the CLI and the HTTP route cannot drift into two
different truths, and read the credential symbol out of the file instead of
guessing its name. Implementation:
`references/status-probe-not-a-hardcoded-field.md`.

### A 400 on `pairing-code` is a dead end, not a workaround

`POST /api/sessions/<id>/pairing-code` with `{"phoneNumber": "+91…"}` returns a
bare `400 {"message":"Bad Request"}` — no field name, no reason. The QR itself is
served by `GET /api/sessions/<id>/qr` (`{"qrCode": "data:image/png;base64,…"}`)
and works fine, so the failure is specific to the pairing-code DTO. Do not spend
a session guessing bodies against it.

Pairing requires the phone: **WhatsApp → Settings → Linked devices → Link a
device.** Surface the QR and stop. Never ask the user to paste a code or session
material. If a numeric-code flow is genuinely needed, offer to hold the QR
fresh on a screen the user can scan from their own handset.

### Route surface worth knowing on this gateway

| route | response | note |
|---|---|---|
| `GET /api/health` | 200 | channel-level only, says nothing about pairing |
| `GET /api/sessions` | list | `[]` means nothing is paired |
| `GET /api/sessions/<id>/qr` | base64 data URL | regenerates constantly; always fetch fresh |
| `POST /api/sessions/<id>/start` | 400 | `"Session is already started"` — **not** a fault, the session is alive |
| `POST /api/sessions/<id>/pairing-code` | 400 bare | DTO constraint, no usable detail |

`"Session is already started"` reads like an error and is actually proof the
session exists. Confirm the key first — an unauthenticated `GET /api/sessions`
returns `{"message":"API key is required"}`, which is the header being wrong, not
the gateway being down.

### Server crash on missing QR file
- If `qr.png` doesn't exist at boot, server crashes with `ENOENT`
- Fix: guard `fs.existsSync(QR_PATH)` before `fs.statSync()`
- Fix: `fs.mkdirSync(path.dirname(QR_PATH), { recursive: true })` before write

### Tunnel instability
- Serveo and localtunnel both unreliable from this container
- Public tunnel URLs time out externally
- Best path: local dashboard access, or send QR image directly

## Environment constraints

**Check before assuming anything about privileges.** This skill has been used
on two very different hosts:

- Locked agent container running as `hermes` (uid 10000) — **no `sudo`, no
  `su`, no Docker socket access, no `setcap`.** Do not attempt root
  escalation from inside the agent. For system package installs, instruct the
  user to run commands in their own root shell.
- A root-capable VPS with working `docker`/`docker compose` (sometimes
  requiring `sg docker -c '...'` to reach the socket).

Run `id` and `docker ps` once at the start of a session rather than reading
either answer off this file. If `/etc/sudoers` write fails, stop and ask the
user to run it in their root shell; do not retry the same path.

## Verification signals

After WhatsApp action, verify:
- message text appears in chat history
- message input box is empty
- no error toast/notification visible
- if any fail, report and stop rather than retrying

## Anti-patterns to avoid

- Don't retry the same CDP call after timeout — pivot to Playwright
- Don't use default Playwright UA on WhatsApp
- Don't blind-retry keyboard input if React state doesn't sync
- Don't iterate tunnel methods that already failed — report and pivot
- Don't send bulk unsolicited messages in tight loops
- Don't loop on privilege escalation in locked containers
- Don't assume an auth header name — 401 with a correct value is the app
  rejecting the *header*, not the key
- Don't report a gateway as unreachable without checking the **session** status.
  A healthy API on a listening port with a `qr_ready` session is an unpaired
  account, and pairing is a human step — surface the QR and stop
- Don't guess bodies against a bare 400 on `pairing-code`; the QR endpoint works
  and pairing needs the phone regardless
- Don't collapse "service reachable" and "account usable" into one status field
- Don't treat a 200 as proof a route or spec endpoint exists when an SPA is
  mounted at the root; check the body is JSON
- Don't guess request bodies against a bare 400 — read the compiled DTO
- Don't use a space in a generated session/slug name unless the schema
  explicitly allows it
- Don't decode a container's route contract from the minified frontend
  bundle when the compiled server code is available
