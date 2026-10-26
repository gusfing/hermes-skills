# X/Twitter session facts (verified 2026-09-29)

Drive X from a **real browser session** on the same host that handles other
social work. These are the observable facts, not setup steps.

## Logged in != can DM. The passcode gate is separate

A fully logged-in X account can still be completely unable to open its DM
inbox. DMs are encrypted with an account passcode:

- `x.com/messages` and `x.com/i/chat` both redirect to
  **`/i/chat/pin/recovery`**
- Body: *"Enter Passcode — Your passcode is required to recover your
  encryption keys so we can decrypt your previous messages."*
- The agent cannot set, guess, or read it. Only the user knows it.
- No "skip" — the inbox is unreachable until they enter it.

**Raise this at login time, not when the first DM is due.** Ask whether the
account has DM history. A brand-new account has an empty inbox, so "Forgot
passcode" costs nothing and unblocks the feature immediately. Discovering it
at send time wastes a round trip.

## Verify login by page state, never by cookie

`auth_token` reads `false` in page JS **even when fully logged in** — it is
HttpOnly and invisible to `document.cookie` by design. A probe that concludes
"logged out" from an absent `auth_token` manufactures a false negative.

Positive signals (all observed together on a live session):

| Signal | Value |
|---|---|
| URL | `https://x.com/home` |
| title | `Home / X` |
| tweet composer | `tweetTextarea_0` present |
| account menu | `SideNav_AccountSwitcher_Button` present |
| nav self-link | `/Kunalsharmadec6` |

The handle loads **asynchronously** — reading it immediately after `goto_url`
returns blank and looks like a failure. Read it after a delay, or take it from
a nav self-link, which is present in the same snapshot as the other signals.

## Testids

| Thing | Selector |
|---|---|
| DM tab | `AppTabBar_DirectMessage_Link` (**not** `Message`) |
| Tweet composer | `tweetTextarea_0` |
| Account switcher | `SideNav_AccountSwitcher_Button` |

`/i/messages/compose` is a **404**. There is no direct compose URL; go through
the DM tab.

## Tab loss is silent

A foreground browser command that hit its timeout took open tabs from 12 to 1.
The Chrome profile survived, so the login did not need repeating, but every
in-flight tab was gone. **Background every command that navigates or loops**
(`background=true, notify=true`). A foreground timeout costs a workspace; a
backgrounded command costs nothing.

Reopening a tab that was lost does not require re-login — the session lives in
the profile, not the tab.

## Report what was not tested

Posting, DMing, and timeline reading were never exercised on this session.
Say so explicitly. "Logged in" and "can post" are different claims, and only
the first was measured.
