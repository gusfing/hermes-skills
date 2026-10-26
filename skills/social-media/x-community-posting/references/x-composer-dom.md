# X composer DOM — measured, not guessed

Every selector here was read off the live DOM on `@Kunalsharmadec6`
(2026-09-29) by dumping elements. **All of my first guesses were wrong.**
When a selector misses, dump the DOM before concluding a feature is missing.

## Verified selector table

| Element | Selector | Notes |
|---|---|---|
| composer (feed) | `[data-testid^="tweetTextarea"]` | `tweetTextarea_0` on `/home` |
| composer (reply dialog) | `[data-testid="tweetTextarea_0"]` **scoped inside** `[role="dialog"]` | same testid as feed — see collision |
| audience button | `button[aria-label="Choose audience"]` | **no `data-testid`**; text reads "Everyone" |
| audience, after pick | `button[aria-label="Change audience"]` | its text IS the community name — read to confirm |
| community rows | `role="menuitem"` | inside `[data-testid="cellInnerDiv"]`, virtualized |
| post button (feed) | `[data-testid="tweetButtonInline"]` | |
| post button (reply) | `[data-testid="tweetButton"]` | different testid from feed |
| reply open | `[data-testid="reply"]` on the target `article` | |
| new DM search | `input[data-testid="new-dm-search-input"]` | inside the compose dialog |
| modal mask | `[data-testid="mask"]` | intercepts pointer events |

## Trap — the picker renders only a SLICE of your communities

The audience picker mounts only a few at a time. Measured visible on first
open: Build in Public, Indie Hackers, SaaS & AI, Indiemakers and SaaS
founders, Branding & Brand Design. `Bootstrapped Startup Founders` was
**not** mounted, and a plain scan reported `community row not found` — which
is indistinguishable from "you are not a member of that community."

Three fallbacks, in order, all verified working:

1. direct scan of `[role="menuitem"]`
2. type into the picker's own search input, then re-scan
3. `mouse.wheel(0, 420)` to scroll the virtualized grid, re-scanning each time

## Trap — the reply dialog collides with the feed composer

The home composer is *also* `[data-testid="tweetTextarea_0"]`. A global query
types into the feed **behind** the reply modal; the dialog's Reply button
then stays `disabled` forever. The click returns no error and no reply is
posted — the script reported success. This silently lost a reply once.

**Always scope reply interactions to `[role="dialog"]`.**

Cheapest confirmation for a reply: **a real dispatch closes the dialog**.
Poll for the dialog disappearing rather than trusting the click.

## Confirmation is asynchronous

| Check | Observed |
|---|---|
| 6s after dispatch | new post NOT visible |
| 39s after dispatch | visible on profile |
| reply at 30s | visible on `/with_replies` |

Poll the profile feed a few times rather than checking once:
- posts → `https://x.com/<HANDLE>`
- replies → `https://x.com/<HANDLE>/with_replies`

A single check produces a false negative that gets reported as a failed post.

## Confirm against the surface the thing actually lives on

Two false negatives in one session came from checking the wrong page:

- Declared a post **failed** because it was absent from the *community* feed.
  It was live on the *profile* the whole time. The user had to say so.
- Declared the account's inbox **empty** while a passcode-recovery gate was
  intercepting `/i/chat`. The inbox had three real conversations.

When verifying, enumerate candidate surfaces and check them, or prove the
absence is real before reporting it.

## Engagement templates repeat within a session

Pulling reply bodies from a fixed list of 8 substance points produced two
replies in the same run that shared a clause — visibly the same person twice.
Widen the pool and track what was used in the current session.

## Passcode gate blocks the DM inbox

`/messages` → `/i/chat` → `/i/chat/pin/recovery` when DMs are encrypted and
the passcode is unknown. The inbox renders **empty**, which reads as "new
account, no conversations" — it is actually a recovery page. Enter the
passcode, then re-check before claiming anything about the inbox.
