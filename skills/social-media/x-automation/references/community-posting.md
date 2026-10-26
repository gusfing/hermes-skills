# X Community Posting — measured detail (2026-09-29)

Account: `@Kunalsharmadec6`, logged in via a real desktop Chrome on CDP 9222
(no cookies). All values below were read off the live DOM, not inferred.

## Why this looked broken and wasn't

Two separate false negatives, both mine, both from checking the wrong place:

1. I queried `[data-testid$="addAudience"]` → 0 results → concluded "no audience
   control exists." The real control carries **only** an `aria-label`, never a
   `data-testid`. A `data-testid` query cannot see it by construction.
2. Community pages (`/i/communities/<id>`) contain **zero** `[contenteditable]`
   elements, so "there is no composer here" is true and misleading — the
   composer is on `/home` and the community is set as an audience.

**Generalisable rule: when a selector returns 0, confirm the attribute family
before concluding the element does not exist.** Try `aria-label`, `role`, then
`innerText` leaf-matching. X uses `data-testid` for some controls and
`aria-label`/`role` for others, mixed within the same composer.

## Exact selectors

```
composer        [data-testid^="tweetTextarea"]        tweetTextarea_0 on /home
audience button button[aria-label="Choose audience"]  -> "Everyone"
after selection button[aria-label="Change audience"]  -> community name
community rows  [role="menuitem"]                     inside [data-testid="cellInnerDiv"]
post button     [data-testid="tweetButtonInline"]
modal overlay   [data-testid="mask"]
```

Row text includes the member count, e.g. `Build in Public | 267.9K Members`.
Match on `startsWith(name)`, not equality.

## Joined communities (13) with IDs and measured sizes

| Community | ID | Members |
|---|---|---|
| Build in Public | 1493446837214187523 | 267.9K |
| Branding & Brand Design | 1506780333034782720 | 26K |
| Indiemakers and SaaS founders | 1492982239960969222 | 12.9K |
| SaaS & AI | 1669886565928300545 | 8.9K |
| Indie Hackers | 1852284626317754858 | 3.7K |
| Bootstrapped Startup Founders | 1725580569633829064 | — |
| Startup Community | 1471580197908586507 | — |
| Tech Founders | 1824090181827457380 | — |
| build in community | 1521855238277414913 | — |
| Gen Z Founders | 1488914857852383243 | — |
| BuildinPublic | 1495042358068477955 | — |
| Solopreneurs | 1500364132390150144 | — |
| Tiny Startups | 1834888119436345673 | — |

Discovered via `https://x.com/<handle>/communities` — `/i/communities` redirects
to the profile tab. Membership is confirmed by the literal word `Joined` in the
community page body, not by the listing alone.

Note three of these (Build in Public, build in community, BuildinPublic) target
substantially the same audience. Rotating across all three is not diversity.

## Mask trap

`[data-testid="mask"]` sits in `#layers` and intercepts pointer events for the
whole overlay. A normal Playwright click retries for 30s and fails with
`subtree intercepts pointer events`. `force: true` is required. An
`Escape` pressed earlier can leave a mask behind with no visible dialog — check
`pg.query_selector('[data-testid="mask"]')` and clear it before interacting.

## The disabled-button ambiguity

A staged post with `[data-testid="tweetButtonInline"].disabled === true` for
30s straight is ambiguous. It is not necessarily a publish in flight — it can
be a half-committed composer left by a prior Escape/mask sequence. Do not treat
"button disabled" as "probably posted." Reload `/home` and redo cleanly, and
assert `enabled` before typing rather than after.

## Reply path — written, NOT verified

The reply flow (click `[data-testid="reply"]` inside an `article`, type into
`[data-testid="tweetTextarea_0"]`, click `[data-testid="tweetButton"]`) ran
without error and the reply did **not** appear on the profile. "No error" is
the expected result of a lost post, not evidence of one. Fix by dumping the live
reply composer DOM and confirming which Post button belongs to the reply
context — the same dialog-scoped-selector trap seen on LinkedIn, where a
messaging overlay and an invite dialog both contain `[role="dialog"]` and both
carry their own Send/Post button.

Use the same poll-and-assert confirmation as posting. A reply must be confirmed
present on the profile, not merely dispatched.
