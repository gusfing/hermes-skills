# LinkedIn messaging inbox — read recipe (measured 2026-09-30)

Session: desktop Chrome + CDP on `http://127.0.0.1:9222`, logged in as Kunal
Sharma. Feed rendered 14,345 chars, so the session was healthy.

## What the inbox actually looked like

Ten-plus live conversations. Any "the inbox is quiet" read was an artefact of
the selector, not the state:

| Thread | Last activity | Note |
|---|---|---|
| Vikas babu | today 10:14 | conference invite (Phuket, 3–4 Dec 2026) |
| Saied Khan | today 06:35 | answered |
| Utkarsh Saxena | Sep 29 | 2 messages + follow-up, got a non-answer |
| Agnivesh Sharma | Sep 29 | pitching a meeting-booking blueprint |
| Neha Khatri | Sep 28 | asked about the work, unanswered |
| Hinal Akhani | Sep 27 | inbound pitch |
| Aaradhya Bhatt | Sep 27 | inbound pitch |
| Satyam Samele, Sahil Nagpal, Hifza Fatma | Sep 25–27 | older |

## Step 1 — list conversations by innerText

```python
rows = pg.evaluate("""()=>[...document.querySelectorAll('[data-oid], ul li')]
    .map(e=>(e.innerText||'').replace(/\\n+/g,' | ').slice(0,120))
    .filter(t=>t.length>8)""")
```

This returns name + date + last-message preview in one call. Do NOT use
`a[href*="/messaging/"]` as the row filter — it matches only the `Messaging`
nav item and produces a false empty-inbox read.

## Step 2 — open one thread by coordinates

```python
box = pg.evaluate("""(nm)=>{
  const li=[...document.querySelectorAll('li')].find(e=>(e.innerText||'').includes(nm));
  if(!li) return null;
  li.scrollIntoView({block:'center'});
  const r=li.getBoundingClientRect();
  return {x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2)};
}""", name)
pg.mouse.click(box["x"], box["y"])
pg.wait_for_timeout(10000)
```

URL becomes `/messaging/thread/<base64-encoded-id>/`. Confirm the header name
matches before reading anything.

## Step 3 — read messages

```python
SKIP = (r"Press return|Status is|options list|Conversation List|screen reader|"
        r"Reply to conversation|Business Services|Get the LinkedIn app|new feed updates")
msgs = [m for m in pg.evaluate(
    "()=>[...document.querySelectorAll('li')].map(li=>(li.innerText||'').replace(/\\n+/g,' | '))")
    if len(m) > 20 and not re.search(SKIP, m)]
```

Timestamps arrive as `SATURDAY` / `TUESDAY` / `TODAY` markers, not dates.

## Failed approaches, in order

| Attempt | Result |
|---|---|
| `li a[href*="/messaging/"]` to harvest thread URLs | `{}` — rows have zero anchors |
| `li.querySelector('button,a,[role=button]').click()` | returned true, opened nothing, stale thread read |
| `document.querySelectorAll('li')` immediately after | returned the PREVIOUS conversation under the target name |
| `data-oid` on the row | `null` |
| `li:has(a[href*="/messaging/"])` as a row filter | 1 match (nav item) → false "empty inbox" |

The row's only real child is
`button.msg-thread-actions__control.artdeco-butt` — that is the options menu,
not the row activator.

## Why the stale-thread read is the dangerous one

Every other failure here is loud: `{}`, an exception, a null. The
`element.click()` path returns success and yields *a real, plausible
conversation belonging to the wrong person*. Anything that writes a reply from
that will message the wrong human. Verify the thread header after clicking,
before composing.
