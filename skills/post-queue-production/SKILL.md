---
name: post-queue-production
description: Use when building a post queue for the owner to review.
---

# Post queue production

A day-ahead queue of drafts the owner reviews, edits and publishes by hand.
This is the class: "get tomorrow's posts ready for me to look at."

## The queue is a deliverable, not scaffolding

The owner reads a queue UI and an image. They do not read source files. So the
queue itself is the product, and a placeholder inside it is a finished-looking
product made of nothing.

- **Never write `TODO` into a slot.** A reviewer sees `TODO: number` and reads it
  as written copy. Owner correction, verbatim: `YOU HAVE TO REPLACE`.
- **Empty research means zero posts, not N placeholders.** If the research pass
  produced no usable angle, report that and stop. Scaffolding a queue to fill a
  quota re-breaks the gate that was supposed to prevent it.
- **Every slot must be a different post.** Varying only the first line is not
  distinct — owner correction, verbatim: `NO POST I WANT DIFFERENT POSTS ON ALL
  SLOT`. Vary the body. Prove it, don't eyeball it:

  ```python
  lis = [s['linkedin'] for s in slots]
  assert len(set(lis)) == len(lis), 'duplicate posts in queue'
  ```

  **That assertion does not catch the failure that actually happens.** It
  hashes the whole message, and a queue built by varying only the hook line
  has 9 distinct messages sharing one body — so it passes. Measured 2026-10-07
  on the `queue/2026-10-06/` day: **7 of 10 slots** (`03,04,06,07,08,09,10`)
  were byte-identical after line 1, differing only in first line, and the
  documented check would have waved them through. Only `01`, `02` and `05` were
  genuinely distinct.

  **Glob every slot, not just the single-digit ones.** The first audit of that
  day globbed `0*_linkedin.txt` and found "6 of 9" — it silently excluded
  `10_linkedin.txt`, which shares the same body. Number your slots and sort
  numerically, or glob `*_linkedin.txt` and strip the extension; a pattern that
  works at 9 slots is wrong at 10.
  Hash the body *after* the hook:

  ```python
  def body_of(text):                     # queue files are `hook\n\nbody`
      p = text.strip().split("\n\n", 1)
      return p[1].strip() if len(p) == 2 else text.strip()
  bodies = [body_of(s['linkedin']) for s in slots]
  assert len(set(bodies)) == len(bodies), 'distinct hooks, identical bodies'
  ```

  Distinct hooks over a shared body is the pool-post pattern wearing a costume,
  and the owner has already rejected pool posts (`No these posts will never
  gets views`). Report the collision before the queue is handed over — 6 copies
  of one paragraph published in a single day is visible to every reader.

- **If the owner answers `i don't know` to a which-one question, stop asking.**
  Pick the strongest option yourself, give the reason in one line, and deliver
  it for rejection rather than for approval. A second identical question after
  `i don't know` is an unmade decision handed back.

- **Confusion is a stop signal, not a status update.** Owner corrections,
  verbatim: `Bro what are you going I'm confused lets rethink stufff` and,
  after a batch of drafts and research landed at once,
  `no stop everything you are not doing anything good`. When the owner signals
  confusion, **halt tool work** and reply with plain language only: what is
  currently live, what is stopped, what is pending, and at most three ways
  forward. No new drafts, no new research, no new cards in that reply. Doing
  more work while someone is confused is what confused them; the fix is a
  state of the world they can read in ten seconds, then one decision.

- **Deliver one thing, not a bundle.** A pick followed by three hook options,
  a full draft, a rendered image, a queue warning and a score in the same
  message reads as a dump even when every piece is correct. Ship the single
  deliverable, then the next thing after they respond.

- **Slot count and times are owner overrides.** `ONLY 2 POST ON LINKEDIN FOR NOW
  ONE IN MORNING AND ONE IN 3:15PM` replaced a generated 10-slot plan. Apply the
  override as given. Do not pad back to a default, do not ask if they're sure.

## The owner supplies the image now (2026-10-11 override)

Standing workflow, owner directive verbatim: `YOU MAKE THEM AND TELL ME I WILL
CHECK THEM AND THEN MAKE THE IMAGE MY SELF OR ADD PDF AND THEN YOU POST THEM
WITH THE IMAGE`. So: draft the text, put it in front of the owner, **stop**, and
wait. The image/PDF comes back from them and the post publishes with it.

Do not pre-render a card to fill the slot. Rendering unasked pre-empts a choice
the owner explicitly said they'd make, and the earlier correction
`Can you add images yourselves` is now superseded as a *default* — it still
applies when they ask for a card. `scripts/make_card.py` stays as the fallback
renderer for that case (`Can you add images yourselves`, 2026-10-07), never as
the default path.

This also means the image half of "every post ships with an image" moves from
the assistant's to-do list into the queue's **review state** — a slot without an
image is not a defect, it is a slot waiting on the owner. Show it that way
instead of blocking on it.

Render the card rather than generating it: on a text card the words **are** the
content, and a diffusion model will happily render `clarity` as `clariry`. HTML
into headless Chromium produces exact glyphs, deterministic every run, no API.

- LinkedIn: **1080x1350** (4:5 portrait). X: 1600x900.
- One accent colour per slot so a grid of them never looks like one image.
- **Wrap copy at sentence boundaries, never at a char limit.** A subtitle that
  stops at `...the tools are not the` reads as a bug. Cut back to the last
  `. `, `! `, `? ` inside the limit; if there is none, end on a whole word and
  append `...`.
- **Look at the rendered PNG before attaching it.** The failure mode is a cut
  line or an overlapping footer, and neither shows up in the byte count. Confirm
  the subtitle ends on a complete sentence, then attach.
- **The headline must read standalone.** The card quote is lifted out of the
  post body, which carried it in context. A body fragment like
  `The line isn't can AI build hard things. It's does the mistake announce itself.`
  reads as broken English at headline size. Ask the vision pass for the layout
  **and** whether the headline is a complete grammatical statement — a
  layout-only question returns `all clear` on a card that reads wrong.

## Score the copy before you render it

A queue of well-formed posts that all score as machine-written is not a
finished deliverable. Run the humanizer pack over every draft, fix the flagged
check, then render. The check that fails in practice is SPECIFICITY, and it is a
*density*: markers count absolutely, the score is per 100 words, so the fix is
always both more named markers **and** fewer words.

Anonymous attribution (`someone replied`, `one reply said`) burns markers and
buys nothing — the harvested thread already holds the name and the count.
Naming one source and cutting ~150 words moved a draft from 45.2 to 85.5.

Mechanics, thresholds and the full before/after:
`references/passing-the-humanizer-gate.md`.

## Chat is the interface the owner actually works in (2026-10-12 override)

Owner directive, verbatim: `DASHBOARD IS CONFUSING AND I DONT UNDERSTAND IT CAN
YOU JUST DO ONE THING I SEND YOU IMAGE HERE YOU USE THAT OR PDF`.

So the review loop is **in this chat**, not in a web UI. The standing flow is:

draft the text → put it in the chat → **say nothing was posted** → wait for the
owner's image/PDF → publish with it.

Consequences to apply without asking:

- **Never route the owner into the calendar UI to review or approve.** Do not
  send the tunnel URL as the way to check work, and do not treat "the UI shows
  it as ready" as the review step. The owner reads the post where you pasted it.
- **A URL and a password are not an interface.** Handing over a link plus a
  credential pushes the work back onto the owner. When they ask what the
  password is, the answer to the *real* request is "you don't need it — send me
  the image here". Offer the password if they still want it; do not lead with it.
- **A confusing surface is a failed surface, not a training problem.** The owner
  is technically strong (SSH, systemd, firewalls). When someone with those
  skills says a tool is confusing, the tool lost. Do not respond with an
explanation of how to use it; remove the need for it.
- **Publishing-side plumbing is still worth fixing.** The reason the chat flow
  works at all is that attach-on-publish was verified end to end
  (`input.files.length=1`, preview rendered, Post enabled, stopped short of the
  click). "The UI is out of the loop" is not "the pipeline is out of the loop".

The calendar UI work below still stands as engineering — keep it correct if it
is ever used — but it is no longer the owner-facing path.

## The calendar UI, when a UI is actually wanted

`studio.py` serves the content calendar (port 8792, basic auth, systemd user
unit). **Superseded as the owner's primary interface** by the chat override
above; still the surface to keep correct for the cases where a visual queue is
explicitly requested.

- **Derive review state, never store it.** `ready` = has body + has image + no
  `TODO`. Old state files keep working and nothing can drift out of sync with
  the copy it describes. Add an explicit `approved` flag only when the review
  loop genuinely needs to record a human decision.
- **Give the owner a `needs me` filter and a `ready n/N` chip.** Review-first
  means slots sit waiting on a human; that turns it into one glance instead of
  reading every card. The owner's own workflow step should be the most visible
  thing on the page.
- **Verify with a live DOM probe, not an HTTP 200.** A 200 and a JS syntax check
  both pass on a page that paints nothing. Measure cards rendered, filter
  counts, editor-opens-on-click, and `console_errors == []`.
- **Measure layout, don't eyeball a screenshot.** Overlap and overflow are
  `getBoundingClientRect` arithmetic. A full-page vision pass timed out while
  the arithmetic answered in one call. Check phone width too — the owner reviews
  from his phone.
- **A UI guard must be provable-failing.** Mutate a copy of the state through
  the real server, re-measure, restore the original bytes — and assert the bytes
  match afterwards. A badge that always reads `ready` is not a guard; it is
  decoration.

Probe code, the anchor-injection pitfall, and the measured before/after:
`references/review-first-calendar-ui.md`.

## Report publish state unprompted

After building a queue, say in the same message whether anything will actually
go out. Owner correction: `You haven't posted yet why`. Building a queue and
then going silent about its state reads as "I posted" even when nothing did.

**Nothing publishes from here by standing instruction** (`Dont post it yet send
me here`). The queue writes draft files. Publishing stays a separate, explicit,
owner-approved step — and arming a timer is a thing you ask for, not a thing you
finish the job with.

## Verify before you hand it over

Assert the whole deliverable in one pass — length bands, distinctness, image
attached, times correct in the owner's zone, and zero placeholders:

```python
assert all(1599 <= len(s['linkedin']) <= 1855 for s in slots)   # measured band
assert all(s['image'] for s in slots), 'slot without image'
assert 'TODO' not in json.dumps(slots), 'placeholder shipped'
```

Slot times are wall-clock in the owner's zone, converted to UTC only for
display. Expected times in tests are computed from the tz database, never
hand-written — see `timezone-aware-scheduling`.

## Related

- `references/passing-the-humanizer-gate.md` — the five detector checks and
their thresholds, why SPECIFICITY is a density, and the card-headline
standalone-grammar check
- `grounded-post-writer` — whether the copy is worth posting at all (specificity
  gate). Overlaps on post construction; this skill owns queue assembly and
  delivery. It is user-owned and needs `hermes curator adopt grounded-post-writer`
  before curation can edit it.
- `references/review-first-calendar-ui.md` — upgrading the calendar UI: derived
  review state, the `needs me` filter, the three probes (DOM, layout, provable
  failing), and the embedded-JS anchor pitfall
- `timezone-aware-scheduling` — slot times, DST-safe test expectations
- `no-comments-guard` — comments off, posting only
