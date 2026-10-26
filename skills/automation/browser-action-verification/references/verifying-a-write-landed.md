# Verifying that a write actually landed

When a script posts, comments, likes, DMs, or deletes, the click is not
evidence. The check afterwards decides whether you report success or failure —
and a check that reads the wrong thing produces confident false negatives that
are worse than no check at all.

## The rule

**Verify on the transport, not the rendered view.** A control counts only if it
reads state the platform itself changed.

| action | control that works | control that lies |
|---|---|---|
| like / react | aria-label flips `"no reaction"` → `"reaction"` | counting visible buttons |
| comment | `POST .../createComment` → **HTTP 200** | editor cleared; page text; absence from a tab |
| form submit | HTTP 2xx on the POST | click returned, spinner stopped |
| deletion | the **gone-marker** in the permalink (`page doesn't exist`) | "no article rendered" |

## Why this is worth a reference

Session 2026-09-30, LinkedIn: four consecutive "comment failed" reports while
every comment had published. `createComment` returned 200 throughout. The
verification scraped `document.body.innerText` and checked the post was absent
from `/in/<you>/recent-activity/comments/`. Both are unreliable immediately
after a write — the view lags, paginates, and may not be rendered. The send
was never broken; the check was.

Same session, same class: after deleting a post, the permalink still renders a
page. It renders a *tombstone*. "No article found" and "post deleted" are
indistinguishable by article presence alone; only the explicit gone-marker
(`page doesn't exist`) settles it. Three wrong conclusions came from that one
ambiguity — including "it's still there" and "the delete failed" for a post
that was already gone.

## Implementation

```python
# enable Network, drain stale events, act, then require the status
Network.enable
# ... click / submit ...
wait up to ~20s for Network.responseReceived where url contains the action id
require status == 200
```

Response **bodies** for these requests are unreliable —
`Network.getResponseBody` can return `-32000 No data found for resource` even
when the write succeeded. Take the **status code** and ignore the body.

Drain stale events *before* acting, or a leftover response from a previous tick
gets attributed to this one.

## Negative results

`absent is not proof of absence`. When a check returns "not found" and that
contradicts expectation, find the **positive marker** the platform emits for the
thing being gone and require that instead. A view that is supposed to refresh
after a write is the least reliable control.
