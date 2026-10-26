---
name: x-social-poster
description: |
  Post to X using Camofox browser automation. Supports text posts,
  media/image posts via browser composer, template-based outreach,
  and scheduled posting workflows. Uses existing Camofox REST API;
  no X Developer API access required.
version: 1.0.0
tags: [x, twitter, posting, social-media, camofox, automation]
---

# X Social Poster

Use this skill when the user asks to:
- post text or media to X/Twitter
- schedule X posts or run outreach sequences
- automate X composer flows in Camofox
- send templated DMs or replies

## Prerequisites

1. **Camofox running** at `CAMOFOX_URL` (typically `http://localhost:9377`)
2. **Logged-in X session** for the target account in Camofox
   - import cookies with `/sessions/{userId}/cookies`
   - use the same `userId` + `sessionKey` to preserve login
3. **Browser tools available**:
   - `navigate`, `snapshot`, `click`, `type`, `press`, `evaluate`, `screenshot`

## Session model

- `userId` = one X account identity
- examples: `x_account_a`, `x_account_b`
- `sessionKey` reuse keeps the browser profile stable

## Posting workflow

### 1. Verify login state

```
GET /sessions/{userId}/cookies -> POST import
POST /tabs  (url: https://x.com/home)
GET  /tabs/{tabId}/snapshot
```

Confirm logged-in refs:
- `Account menu` with display name
- `Post` link in primary nav
- compose textbox within home page

Do not attempt posting if these are absent.

### 2. Choose post type

| Type | Recommended path |
|---|---|
| Text only | Inline composer form |
| Image post | Composer media button/file input |
| Reply | Navigate to status permalink then composer |
| Thread | Repeat composer in thread mode |

## Text-only posting flow

1. Open `https://x.com/compose/post`
2. If redirected to home, click `Post` nav ref or use JS:

```
evaluate: () => {
  const btn = [...document.querySelectorAll('[data-testid="tweetTextarea_0"], [data-testid="tweetButtonInline"], [href="/compose/post"]')]
    .find(el => el.offsetParent !== null);
  if (btn) btn.click();
}
```

3. Wait and snapshot again
4. Type post body into textbox with `data-testid="tweetTextarea_0"` or visible textbox
5. Press `Enter` or click `Post` button
6. Verify via next snapshot/screenshot

## Image posting flow

### Approach A: hidden file input selection

1. Open compose modal/page
2. Run JS to locate the file input:

```
const input = document.querySelector('input[type="file"][accept*="image"], input[type="file"][accept*="media"]');
return input ? { tag: input.tagName, id: input.id, cls: input.className, exists: true } : { exists: false };
```

3. If found, attempt `evaluate` with a Blob URL assignment does NOT work for security; instead:
   - use visible `Choose File` button ref from snapshot
   - snapshot refs often include `button "Choose File"` in X composer toolbar
   - click it and rely on Hermes runtime to complete upload path if supported

### Approach B: paste trigger

1. Focus compose textbox
2. Use `evaluate` to dispatch a paste event with image data URL if the runtime exposes a way to inject image data
3. Verify attachment preview appears before submitting

### Approach C: post image after manual upload in same session

If automation cannot complete upload:
- stop before submit
- report the exact composer state
- let user complete upload manually in Camofox
- resume automation for submit button click

## Composer reliability heuristics

- X compose is stateful and fragile
- Always re-snapshot after every click
- Use `evaluate` as a complement, not replacement, for ref clicks
- If `Post` button is disabled, check for:
  - empty textbox
  - failed media upload
  - rate-limit/suspension banners

## Submission and verification

1. Submit post
2. Capture screenshot immediately
3. Scan snapshot for success indicators:
   - URL containing `/status/`
   - toast/notification containing success wording
   - timeline article for the new post
4. If none found within 2 retries, treat as failure and stop

## Safety rules

- never loop posting without confirmation of each send
- stop after one failure and report state
- do not retry when verification criteria are not met
- store post outcomes: success/failure/screenshot/timestamp/error

## Templates

Support optional templates under:
- `outreach/intro.md`
- `outreach/followup_1.md`
- `outreach/followup_2.md`
- `outreach/optout.md`

Node: personalization first, send volume second.
