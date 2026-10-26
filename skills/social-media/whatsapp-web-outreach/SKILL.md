---
name: whatsapp-web-outreach
description: |
  Outreach on WhatsApp via browser automation. Uses **local Chrome CDP as
  primary backend** (stable, fast, verified in this environment), with
  Camofox available as a fallback when account isolation is needed.
  No official WhatsApp API required.
version: 1.1.0
tags: [whatsapp, outreach, messaging, social-media, automation]
---

# WhatsApp Web Outreach

Use this skill when the user asks to:
- recruit/outreach on WhatsApp
- send outreach messages through WhatsApp Web
- run a WhatsApp follow-up sequence
- prospecting workflow on WhatsApp

## Backend selection

```
Local Chrome CDP → fallback → Camofox
```

### Primary: Local Chrome CDP (127.0.0.1:9222)
- Attach via Hermes: `/browser connect http://127.0.0.1:9222`
- Uses the user's existing Chrome profile with WhatsApp already logged in
- Stable, fast, no additional server needed
- **Multi-account**: launch Chrome with separate `--user-data-dir` per WhatsApp number
  - e.g. `--user-data-dir=/opt/data/chrome-profiles/wa_account_a`
  - Store the profile path settings somewhere shared so both the user and automation refer to the same dir
  - Reusing the same profile preserves login state across runs; no fresh cookie imports needed

### Fallback: Camofox
- Use only when CDP is unavailable or when anti-detect browser behavior is explicitly required
- Requires Camofox server running and a dedicated `userId` per account
- Keep identities isolated: `wa_account_a`, `wa_account_b`
- Reuse same `userId` + `sessionKey` to preserve chat history

## Required setup

1. Chrome running with remote debugging:
   ```bash
   /usr/bin/google-chrome-stable \
     --remote-debugging-port=9222 \
     --user-data-dir=/opt/data/chrome-profiles/wa_account_a \
     --restore-last-session
   ```
   - First run: complete WhatsApp Web QR login manually
   - Subsequent runs: session persists in the profile dir

2. Confirm WhatsApp Web loads and shows chats at `https://web.whatsapp.com`

3. Attach Hermes browser to CDP:
   ```bash
   /browser connect http://127.0.0.1:9222
   ```

4. Operate responsibly:
   - respect WhatsApp TOS and anti-spam limits
   - cold outreach may trigger bans or rate limits
   - add delays between sends

## Discovery workflow

Goal: open a few likely chat surfaces and inspect them.

1. Navigate to `https://web.whatsapp.com` (or verify current URL via snapshot)
2. From the loaded contact list/chat UI, use refs to:
   - open a target contact
   - read the latest message history
3. If a contact is not present, decide whether to:
   - open `https://wa.me/<number>` style link, or
   - create new message via new-chat UI (`+ New chat` button)

## Outreach script templates

Use templates the user can edit:
- `outreach/intro.md`
- `outreach/followup_1.md`
- `outreach/followup_2.md`
- `outreach/optout.md`

Store under a fixed directory the user can reference.

## Messaging workflow

1. Resolve target by ref from snapshot.
2. Confirm it is the expected contact before sending:
   - check contact name in the chat header
   - verify last message history matches expectations
3. Fill the message box with the chosen template.
4. Send and capture resulting snapshot for verification:
   - message appears in chat history
   - message box is cleared

### Message box reference pattern (CDP)
```js
// Find the active message input box
const candidates = [
  '[contenteditable="true"][data-tab="10"]',
  '#main > footer .x1hx74kb',
  'div[spellcheck="true"]',
  'footer div[contenteditable="true"]'
];
const box = candidates
  .map(s => document.querySelector(s))
  .find(el => el && el.offsetParent !== null);
return box ? 'found' : 'not_found';
```

### Send pattern
- After typing, send with Enter (browser_press key=Enter)
- Do NOT click Send button via ref if ref is unreliable; Enter is consistent

## Safety rules

- never send bulk unsolicited messages in tight loops
- add delays between sends (>= 3 seconds minimum)
- log sent/response status per contact
- stop and surface errors instead of retrying blindly
- if CDP backend becomes unavailable, fall back to Camofox and report the switch

## Verification signals

After send, verify in the same snapshot or next one:
- message text appears in chat history
- message input box is empty
- no error toast/notification visible
- if any of these fail, report and stop rather than retrying

## Tool mapping

These Hermes tools map to this skill:
- `browser_navigate`
- `browser_snapshot`
- `browser_click`
- `browser_type`
- `browser_press`
- `browser_console` (for JS probes when refs are unreliable)
- `terminal` (to launch Chrome with custom `--user-data-dir`)

## Fallback decision matrix

| Condition | Action |
|---|---|
| CDP reachable, WhatsApp logged in | Use CDP directly |
| CDP reachable, WhatsApp not logged in | Surface QR prompt, user scans, retry |
| CDP unreachable | Switch to Camofox, report degradation |
| Camofox composer refs unreliable | Stop, report exact URL/snapshot/screenshot |

## Cookie-backed SSO caveat

Successful cookie import does not guarantee active site login.
Observed: ChatGPT accepted cookies but still rendered login UI.
Always verify with page-state evidence, not HTTP status alone.
