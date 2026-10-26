---
name: session-paste-security
description: Handle pasted session cookies without leaking them.
---

# Session Cookie Handling

When a user pastes a session token (LinkedIn `li_at`, X `auth_token`, any
`sessionid`), it is now in the conversation and will outlive the task. Treat it
as compromised from the moment it arrives, not after something goes wrong.

## Before the user pastes

Say these three things, once, briefly. Then let them decide.

1. **A session cookie is the account.** Whoever holds it is logged in as them —
   can post, message, accept connections. It is not a config value.
2. **It lands in transcript history permanently.** If that matters, the manual
   browser login route is cleaner and no token is ever shared.
3. **It may not work anyway.** Anti-bot systems block the session, not just the
   browser. Do not promise the paste will succeed.

## Handling

- Write to a gitignored path, mode `600`, outside the repo. Never a project dir.
- Prefer the narrowest useful subset of cookies. `li_at` + `JSESSIONID` is
  usually enough; a full 30-cookie dump is a bigger target for no gain.
- Never print cookie values back. Print names and counts only.
- Do not put them in a command line — process args are world-readable via
  `ps`. Use a file, or stdin, or an env var from a protected file.
- Delete the file when the task ends unless the user asks for a persistent
  session. Say whether you deleted it.

## End of task

Tell the user explicitly to rotate: log out everywhere, log back in, new
token. Name the specific cookies that were exposed. A rotated token is the
only real remediation — deleting your local copy does not un-leak it.

## What is NOT a credential worth sending

If a task only needs to read public pages or draft content, say so and skip all
of this. Do not ask for a session token to do something that needs none.
