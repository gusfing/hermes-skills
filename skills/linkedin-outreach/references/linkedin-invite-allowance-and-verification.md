# LinkedIn invite allowance + send verification — measured 2026-09-29

Session-specific detail behind the rules in `SKILL.md`. Read-only probes plus
three real sends on a free account. All numbers below are observed, not
inferred.

## The allowance, verbatim

The counter only appears AFTER "Add a note" is clicked. Before that the dialog
shows only:

```
Add a note to your invitation?
Personalize your invitation to Punit Khatri by adding a note.
LinkedIn members are more likely to accept invitations that include a note.
  [Add a note]  [Send without a note]
```

After clicking "Add a note":

```
Send unlimited personalized invites with Premium
You're out of free custom notes. Bypass the limit with Premium, write
longer notes, and make your profile stand out.
Plus unlock and message all your viewers
```

At the start of the month the same slot read
`3 personalized invitations remaining for this month.` and the field showed a
live counter of `0/200` while the dialog's own prose said "limit personal note
to 300 characters". **The 300 in the text is wrong; 200 is enforced.**

## Measured allowance decay

Read from the dialog on each subsequent profile during one run:

```
before 1st send:  3
after  1st send:  2
after  2nd send:  1
after  3rd send:  0   ("You're out of free custom notes")
```

Two independent signals, agreeing.

## Selector attempts that failed, in order

Recording these because each looked plausible and each cost a round trip.

| Attempt | Result |
|---|---|
| `get_by_role("button", name="Connect")` | 0 matches — the control is a link, and its name is "Invite X to connect" |
| `h1` for profile name | `[]` — no `h1` on a public profile; name is in `h2` |
| `inv.click()` on the Connect `<a>` | nothing happened, no dialog at all |
| nav-dup Connect link after scroll | intercepted by the "For Business" dropdown |
| `[role="dialog"] [contenteditable]` for the note | **would have typed a DM to a stranger** — the messenger compose box is also inside a dialog |
| `get_by_role("button", name="Send")` unscoped | matched the messenger's Send, not the invite dialog's |

The working chain:

```
page.goto("https://www.linkedin.com/preload/custom-invite/?vanityName=<vanity>")
  -> [role="dialog"] filter(has_text=/invitation/i)
  -> button[aria-label="Add a note"]                    (noted path)
  -> textarea.connect-button__send-invite              (NOT contenteditable)
  -> read back input_value() and compare               (must match, else abort)
  -> dialog-scoped button matching /^\s*send\s*$/i
```

`/in/<vanity>/preload/custom-invite/` is the alternate form; it returned a
blank page (empty `document.title`, 0 dialogs) on profiles that rendered fine
moments later. Retry once on the root form before diagnosing.

## Identity check

No `h1`. The name lives in `h2`, and `document.title` is
`"<Name> | LinkedIn"` — though it can be `"(7) LinkedIn"` when a notification
badge is present, so accept a match on **any** of title / h1 / h2, not the
first.

## Control-based verification

A closed dialog is not proof. The check that holds up:

```python
# target page, count invite controls naming THIS person
inv = [a for a in page.locator('[aria-label*="to connect" i]')
       if a.get_attribute("aria-label").lower().contains(who.lower())]
# 0 -> pending;  >=1 -> still contactable
```

Always include an unsent profile as a control. Without one, a render failure
and a pending invite look identical:

```
Saied Khan       -> PENDING (no invite button)
Aditya Poddar    -> PENDING (no invite button)
Atharva          -> PENDING (no invite button)
Punit Khatri     -> 3 invite button(s) = still contactable   <- control
```

## No-note path, verified

With the note allowance at 0, `Send without a note` still sent, and the
target's profile then showed zero invite controls. Same verification applies.
No allowance counter appears on this path — the weekly connect cap is separate
and was not observed being hit.

## Python `random` traps hit while writing the pacer

Both of these are silent until they fire mid-run:

```python
random.uniform(0.8, 2.4)   # returns float -> random.randint(float) raises
random.randint(*GAP_MIN)   # GAP_MIN=70 is an int, so *unpacks the number 70
                            # -> "argument after * must be an iterable, not int"
```

Correct: keep bounds as named ints and pass both, or store the pair as a
tuple and unpack the tuple.

## Unrelated trap found on the same page

`li_connect.py` was run against a JSON pool rather than the DB during part of
this session, so `P.mark(...)` never fired and `outreach.db` recorded **zero**
sends for three that genuinely went out. If the sender can ever read its
targets from anywhere other than the DB, the state store silently diverges
from reality. Check the DB agrees with the platform before trusting either.
