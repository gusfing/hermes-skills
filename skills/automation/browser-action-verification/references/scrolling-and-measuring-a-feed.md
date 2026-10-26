# Scrolling a lazy-loaded feed, and measuring what it does not expose

Session 2026-10-03, LinkedIn. The scroll path cost five dead ends and the
harvest was still capped at 3 posts when I stopped.

## Dead end 1: `window.scrollBy`

Does nothing. `document.body` was `overflow: hidden`, `scrollHeight 793`.

## Dead end 2: assigning `scrollTop` on the element

Works, but **jumps past the lazy-load sentinel**. Assigning `scrollTop = 9000`
put me at 1772 in one step; a single large jump skips the intersection observer
that triggers the fetch, so nothing new rendered.

## Dead end 3: the real scroller still not moving from inside the harvester

`MAIN` is the actual scroller — `overflow-y: scroll`, `scrollHeight 2229` vs
`clientHeight 741`. Scrolling it one screen at a time from a standalone script
worked. The same call inside the harvester did not. Unresolved.

## What worked: real wheel events, and `Input.enable` first

`Input.dispatchMouseEvent` with `type: "mouseWheel"` moved the feed **3 -> 8
cards**. But the first attempt **hung the websocket**.

```
Input.dispatchMouseEvent returns no reply until the Input domain is enabled.
```

`send()` blocks on the socket until timeout. Call `Input.enable` once per
session first. After that the wheel events return promptly.

## When it stops: check whether the bottom is real

The scroll position stabilised at `top: 1539`, and

```
scrollHeight 2280 - clientHeight 741 == 1539
```

That is the true bottom. **3 posts was the whole feed, not a scroll failure.**
Proving the container is at its end converts "my automation is broken" into
"the page served 3 posts" — which changes what you report.

## The metric that does not exist

Every reaction button on the feed rendered:

```
Reaction button state: no reaction
```

**Zero engagement counts in the feed DOM, 0 of 3 posts.** Combined with the
permalink absence already documented in SKILL.md, this means: *a LinkedIn feed
cannot be ranked by performance from the feed itself.* Any "what works on
LinkedIn" claim sourced from feed scraping is fabricated.

## The one dataset that does render

`/in/<handle>/recent-activity/all/` — read live:

```
116 impressions  ·  3 reactions  ·  2 comments
 97 impressions
 48 / 46 / 48 impressions
```

Selectors: `span.ca-entry-point__num-views` for the counter,
`div.feed-shared-update-v2__control-menu-container` for the card. **Zero `<p>`
elements on this page** — a "longest `<p>`" body extractor finds nothing here,
so use container `innerText` plus a noise-line filter instead. Two surfaces,
two different DOM shapes; a selector validated on one is invalid on the other.

## Never guess the handle

`kunal-sharma-9aa97312` -> **404**. The real one, `kunalsharmaai`, came from a
`[componentkey="..._IDENTITY_PROFILE"] a[href*="/in/"]` read off the live feed.
Read identifiers from the DOM; a plausible-looking vanity URL is a silent
dead end. (Same class as the 6 fabricated X handles earlier.)

## Feed-harvest extraction rule that held up

"Longest `innerText`" returns the **card shell** (1,412 chars, starts with the
author). The post body is the **longest `<p>` not inside a modal dialog**
(1,132 chars, the actual first line). Nested cards also duplicate: 27 "Feed
post" elements were 3 real posts. Keep only outermost cards.
