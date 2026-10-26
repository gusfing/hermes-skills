---
name: browser-action-verification
description: Use when confirming a browser write actually landed.
---

# Verifying an automated browser action landed

Class of task: a script posts, comments, likes, DMs, or deletes through a
browser driver, and you must report success or failure. The click is not
evidence. **The check afterwards decides the answer, and a check that reads the
wrong thing produces confident false negatives that are worse than no check.**

## The rule

**Verify on the transport, not the rendered view.** A control counts only if it
reads state the platform itself changed.

| action | control that works | control that lies |
|---|---|---|
| like / react | aria-label flips `"no reaction"` → `"reaction"` | counting visible buttons |
| comment | the create POST → **HTTP 200** | editor cleared; page text; absence from a tab |
| form submit | HTTP 2xx on the POST | click returned, spinner stopped |
| deletion | the **gone-marker** in the permalink | "no article rendered" |

Implementation, and the full incident behind this table:
`references/verifying-a-write-landed.md`.

## Negative results

`absent is not proof of absence`. When a check says "not found" and that
contradicts expectation, find the **positive marker** the platform emits for the
thing being gone and require that instead.

Sharpest instance: after deleting a post, the permalink still renders a page —
it renders a *tombstone*. "No article found" and "post deleted" are
indistinguishable by article presence alone. Only an explicit gone-marker
(`page doesn't exist`) settles it.

Corollary: **a view that is supposed to refresh after a write is the least
reliable control available.** It lags, it paginates, it may not be rendered at
all. Never gate a write report on it.

## Capture the permalink while the card is in hand

Asked to show *what* you liked or commented on, the instinct is to go back later
and look each post up. Do not — act on the card that is already open, and read
the link out of it. The two platforms differ on whether that is even possible.

| platform | link available from the card? | how |
|---|---|---|
| X | **Yes, always** | `/i/status/<id>` resolves without auth |
| LinkedIn | **No** | no permalink, no `urn:li:activity`, no `<time>` |

Measured LinkedIn feed card, every anchor present: `/in/<author>/`,
`/company/<co>/`, `/search/results/all/?keywords=…`, `/`, `"300 reactions"`,
`"Send"`. The timestamp anchor is **`href="/"`**. There is no `data-id` and no
`<time>` element anywhere in the card.

**The activity id is only materialised when a post is expanded or opened.** So
there is no extraction to retry — the attribute is not in the DOM yet. If you
find yourself hunting harder selectors, you are chasing a field that does not
exist; stop and report the limit instead of shipping an extractor that returns
an empty or fabricated URL.

Getting LinkedIn URLs is therefore a **separate, slow pass** that opens each
acted-on post and records the resulting address (~5–10s per post), not a change
to the engagement script. It slows and makes the automation more detectable, so
it is a decision to put to the user, not a silent optimisation.

When a link is genuinely unavailable, show the post text and **say why in the
surface itself**. A blank cell reads as a bug; a stated reason reads as a
design. Revert a working-looking-but-unverified extractor rather than shipping
it — this one produced plausible URLs that could not be followed.

Older rows cannot be backfilled: start recording at the code change. Say the
cutoff date when you hand the surface over.

## Response bodies are not the status

For action POSTs the **status code** is reliable and the **body often is not** —
`Network.getResponseBody` can return `-32000 No data found for resource` on a
request that succeeded. Require the status; ignore the body.

Drain buffered `Network` events *before* acting, or a leftover response from a
previous tick is attributed to this one.

## "It works" needs a source you did not write

A response can look correct and still be served by the wrong process. Before
reporting a deploy as live, confirm the responder is the unit you just started —
a **404 on a route you just added** is the tell, because the process answering
predates the code.

```bash
systemctl --user is-active <unit>.service
systemctl --user show <unit>.service -p NRestarts -p ActiveEnterTimestamp
pgrep -af "[s]erver_name\.py"        # brackets: never match own cmdline
sudo -n ss -ltnp | grep :8791        # who actually owns the socket
```

`NRestarts: 0` plus a fresh `ActiveEnterTimestamp` is the proof. A port that
answers is not evidence — a stale hand-launched copy of the same process will
answer happily with pre-deploy code. A feature route 404ing while the port is
"up" is exactly this, and it invalidates any earlier claim that the feature
shipped.

## A verifier that fails on everything is the suspect

The rule above is about the *check* being wrong. The sharpest form of it: when a
verification pass rejects **every single row**, that is the signature of a check
that inspected nothing, not of uniformly bad data. An empty result set fed into
`any(...)` reports "no match" forever.

An 8s settle after `goto` returned an empty article list; the comparator printed
`MISMATCH` for two URLs that were correct. I was one step from reverting good
data on the authority of a check that had never looked at anything.

**Make every negative check report what it saw** — count of elements inspected,
first element's text — so "found nothing" is distinguishable from "found the
wrong thing". Re-run with a longer settle and a second independent signal before
you destroy anything on the strength of one failure. Details in
`references/hosting-an-internal-dashboard.md`.

## A valid selector scoped to the wrong container is the cleanest false negative

The section above is about a check that inspected nothing. This one is worse
to catch, because the check looks correct: the selector is valid, the
container exists, and the count it returns is a real 0.

Session 2026-10-06. Attaching an image to a LinkedIn composer through raw
`DOM.setFileInputFiles`. Verification was `document.querySelectorAll('[role=dialog] img').length`.
It returned **0 on every pass**, so the run reported
`file set but no image preview appeared` and aborted — for a run that had
**in fact attached the file**. The document-wide image count over the same
interval went **26 -> 30**. The preview never renders inside `[role=dialog]`;
the selector was scoped to a container that will never hold the target.

**Assert on the state the write mutates, not on a UI side effect that may not
render.** The authoritative signal was the input itself:

```js
document.querySelector('input[type=file]').files.length   // 1 after a good set
```

An `img` count is an *appearance* of a successful upload, not the upload.

**Require two independent readings to agree before reporting either way.**
`files.length` plus the document-wide image delta. One reading that fails
while a second unrelated one succeeds is the signature of a mis-scoped check,
not of a failed write — and the failure message must name which step failed,
not flatten every abort into "it did not work".

Same shape, different platform, one line each: a preview scoped to
`[role=dialog] img` reading 0 on success; a dialog-closing check that never
fires because the submit button was `disabled` and nothing was sent.

**Follow-up: `files.length` is necessary, not sufficient.** The same session
later reported `attached, input.files.length=1` on a run whose published post
came back `imgCount: 0`. The input accepted the file; the platform did not end
up serving it — the likely shape is Post clicked before the upload finished,
and a fixed sleep after the set does not prove completion.

So the attach signal has two tiers, and only the second one is the claim:

1. `input.files.length >= 1` — proves the **input** took the file. Use it to
   abort early when the set never landed.
2. the **published artifact** carries the image — the only proof the platform
   uploaded it. Until then say "staged", not "attached".

If tier 1 passes and tier 2 fails, wait on a platform-side completion signal
(an upload progress bar or a network response), not on a timer, and refuse to
click submit until it arrives.

## Rehearse a write up to the irreversible click

A posting script that can only fully publish or do nothing cannot be tested
without publishing — so it never gets tested, and the first run is also the
first real post. Split the path into three tiers, with the dangeriest opt-in:

| tier | does | guard |
|---|---|---|
| dry run (default) | prints the plan: text length, image, hook | exits before touching the browser |
| rehearsal | opens, types, attaches, confirms the submit control is enabled, then **closes** | never reaches the submit click |
| publish | the only path that clicks submit | refuses on empty text or a `TODO` marker in the copy |

The rehearsal tier is what proves the mechanism: the run that validated this
path ended with `attached, input.files.length=1` and
`composer dismissed: yes`. That is a complete proof of everything up to the
irreversible action, obtained without performing it.

**Aborted rehearsals leave state behind.** Returning early on a failed
precondition skips the cleanup, so a composer can be left open holding the
real text. Rehearse must clean up on *every* exit path, and a follow-up check
should confirm the write surface is empty (`dialog: false`, `editorLen: 0`,
`fileInputs: 0`) before the session is called clean.

### The rehearsal's own "clean" line was wrong four times running

Measured 2026-10-12, LinkedIn. Every version of the cleanup reported success
while leaving a live composer holding the full post text — one stray click from
an unintended publish. The failure mode is worth naming as a class, because it
is not specific to LinkedIn:

- the close control was matched on `textContent` and had **only** an
  `aria-label`, so the click never happened and the function returned a
  clean-looking string;
- dismissing the composer **restored** the draft into the page's inline
  composer, so "closed" and "empty" were different facts;
- the verification counted elements that **always** exist (`[role=dialog]`
  matched a hidden video.js modal on a page with no real dialog), so "still
  open" was reported for a clean close and vice versa;
- a **host focus prerequisite** silently voided the clear: the same
  `document.execCommand('delete')` returned `ok=false` on a backgrounded tab and
  `ok=true` after `Page.bringToFront`, while `document.hasFocus()` read `true`
  in both cases — so the obvious focus probe cannot detect it.

Rules that follow, and they generalise past this platform:

- **Require the cleanup command to return a value you can assert on**
  (`'cleared=true len=1'`), not just to not throw. A no-op and a success are
  indistinguishable by absence of error.
- **Never verify with a selector that is present regardless of state.** Ask
  "would this read the same on a dirty page?" — `[role=dialog]` and "editor
exists" both answered yes. Measure the **mutable** thing (trimmed text length),
  and trim it, because editors keep a trailing newline that reads as content.
- **Order is part of the fix.** "Clear then close" and "close then clear" are
  not interchangeable; only the measured order worked. Write the order down next
  to the code, since a later refactor will happily reverse it.
- **Prove cleanliness from a separate script** reading live state, with a
  non-zero exit when dirty. Four consecutive in-script success lines were false.
  Full transcript and the exact ordering table:
  `browser-social-composer` → `references/linkedin-composer-cleanup.md`.

Refuse rather than continue when a precondition fails. A publish that ships
without its image is the failure worth avoiding, and the refusal is also what
makes the next section possible.

## Exclude your own path structurally before attributing an unexpected side effect

A post matching the staged draft was found live on a profile. I could not
prove who published it, and said so rather than guessing.

What *was* provable is the part worth extracting. The live post had **no
image**, and the publish path attaches and verifies an image before it will
click submit — it aborts otherwise. So a completed publish run **cannot
produce a text-only post**. That route is excluded on the code's own terms,
independent of who did the clicking.

**Use a precondition gate as a structural alibi, then state plainly what
remains unknown.** "My publish path refuses to run without an image, and this
post has no image, so it did not come through my publish path" is a real
inference from real behaviour. "So you must have posted it" is not — the gate
excludes one route and says nothing about the others.

Corollary, same session: a diff is how you confirm identity, not memory. Pull
the live text and `difflib.unified_diff` it against the source file. LinkedIn
renders each hashtag as its own block, so a post stored as `#a #b #c` reads
back as three lines plus a blank — strip the UI label before comparing, or a
byte-identical post looks edited and you report a change that never happened.

### The alibi named one route. The answer was in a different one.

Resolution, 2026-10-06. The exclusion above was correct — `--publish` really
does refuse without an image — and the conclusion drawn from it was still
wrong. The post **did** come from my code, through `--stage`.

Mechanism, entirely Python:

```python
CLOSE_JS2 = """(()=>{ ... real close/discard ... })();"""
...
CLOSE_JS2 = """(()=>{ ... the Post click ... })();"""   # mislabelled by an edit
```

The second assignment is the one that binds. `--stage` called `CLOSE_JS2`
believing it was closing, and the last module-level definition of that name
now contained the irreversible click. The run printed its "closed without
posting" lines and posted.

**A duplicate module-level name in a path that gates an irreversible action is
defect even when every branch reads correctly.** Python's last-assignment-wins
makes source order the real control flow, so an edit that relabels a block can
silently re-point the *safety* name at the *dangerous* one, and no test of the
branch logic will show it.

- Give the dangerous action its **own unshared name** (`CLICK_POST`). Never
  let the safety name and the action name be the same identifier.
- Put an explicit refusal on the last line before the step:
  `if not a.publish: return 1` — reachable only from the publish branch.
- `grep -c '^NAME =' <file>` must return **exactly 1** before a gate is trusted.
- When a side effect is found live, **enumerate every path that reaches it.**
  An alibi excluding `--publish` excludes `--publish`, nothing more;
  "therefore not my code" is a second inference that was never earned.

A guard on the name costs one line and is the only thing that catches this
class; a comment saying which block is which is exactly what an edit invalidates.

## Backfilling a field the writer never captured

A missing permalink is often a **capture** bug, not a display bug: the confirm
step searched page *text* for `/handle/status/<id>` when the id exists only in
the `href` attribute, so every post was stored with `null` forever. Symptom
shape: the surface shows "no link stored" for rows that certainly have posts.

Two traps on the repair path, both hit here: matching on a **30-char prefix**
attaches the *wrong* (but real, plausible-looking) permalink because posts share
openings — use a 70-char slice; and **do not take the article's first
`/status/` href**. Measured 2026-10-07: on a status page the first match is the
*inline* link in the tweet body, so one post resolved to the quoted author's
status instead of its own. Take the anchor that contains `<time>`, then open
the URL and assert handle + text slice before citing it. See
`references/reading-conversations-on-x.md`. Reuse the
capture-while-in-hand table above, then re-verify on the network.

## Report the shape of the uncertainty

An action log that counts *my* actions ("23 likes, 16 replies") is not a
result. Say which — engagement received, impressions, signups. If the platform
gates the outcome metric behind a paywall, say so plainly rather than letting
the action count stand in for impact.

Corollary from LinkedIn, where the feed exposes **zero** engagement counts (every
reaction button reads `no reaction`, 0 of 3 posts): when the platform does not
render the metric on the surface you can reach, **say the ranking is unavailable
and name the surface where it is available** rather than substituting post
structure for performance. The owner's own `/in/<handle>/recent-activity/all/`
does render impressions. Five numbers is not a pattern, and "these posts all
carry media" is a census of the feed, not a finding about what works. Route,
dead ends, and the two different DOM shapes:
`references/scrolling-and-measuring-a-feed.md`.

## When did it last run? Build a ledger, not a count

A count answers "how much", never "when". The user will ask when, and if the
answer lives only in a systemd text log the answer is "read this yourself".

A per-run ledger (JSON lines, one row per attempt, outcome vocabulary that
separates *did work* from *correctly did nothing* from *failed*) is the surface
that answers it. Critical detail: **record the runs that never acquired the
resource as well as the runs that did** — if every record call sits inside the
critical section, a run that never got in leaves no trace and is invisible.

Implementation, the outcome vocabulary, and the "it's running needs a scheduled
unit, not a working script" check: `references/scheduled-automation-observability.md`.

## "It looks like the same post" — check the pool, not the defence

When a user reports repetitive or missing-media posts, measure before agreeing
or disputing: list distinct files actually posted, and how much of the pool is
unused. A picker whose fallbacks end in `or pool` converts a thin pool into
**repeats instead of pauses**, and thin it got. See
`references/automated-post-cadence.md` for the reuse-fallback fix, the UTC
timestamp trap in state files, media-by-stem resolution, and why you must not
force a post to prove a feature works. Also: head-slicing a pool so every tick
silently sends zero, persisting a randomised schedule with a day stamp (and the
format-migration trap), audience-local day boundaries, a cap that is defined but
never called, and `/tmp` state files as a 10-day fuse.

## A sentinel that appears in every failure mode is not a diagnostic

The sharpest form of "the check is wrong": when one value comes back
regardless of condition, it is telling you about the reporter, not the thing
being reported.

Raw-CDP evaluate returned `{}` on every probe — `readyState: {}`, `html len: 0`,
`innerText len: 0`. I reported "attached to a non-answering target." Two causes,
neither what I said:

1. My *probe* was wrong: passing a function literal (`()=>location.href`) over
   CDP serializes to `{}`. The expression must be the call (`location.href`).
2. The *wrapper* was wrong: `ev(expr, default=None)` fell back to `default`
   whenever a nested value was missing, so a dead tab and a malformed
   expression were indistinguishable.

**When a probe returns the same value under conditions that must differ,
suspect the probe.** Make distinct failure modes raise differently rather than
degrading to a shared sentinel. A default value that fires on both "no data" and
"wrong input" has destroyed the signal it was meant to carry.

Corollary: an empty result set fed into a comparison reports "no match"
forever. If a check finds nothing where data demonstrably exists, the check
inspected nothing.

## Your own verifier is a probe, and it lies more often than the code does

Auditing a scheduling pipeline on 2026-10-03, six of thirteen checks failed.
Fixing the six turned out to be mostly fixing **the checks**. Four rounds, each
the same mistake:

1. Grepped for `comment` anywhere. `dashboard.py` *displays* comment counts and
   emits none. Tightened to real emission — then flagged `ENGAGE_COMMENTS`, a
   post-*count* range, and the checker's own pattern list.
2. Tightened again, it flagged a line because `createComment` sits inside an
   **f-string message**: `"no HTTP 200 on createComment"`. Fixed by stripping
   docstrings, then `#` comments, then string literals, before matching.
3. Grepped `datetime.now()` and matched the **docstring explaining why naive
   `now()` is wrong**. The fix had just written the sentence the test failed on.
4. A regex for `post(pg, text, community)` truncated at the **first nested
   paren**, reporting 3 text-only calls when all 3 passed an image.

**Rules:**

- **Assert on the assignment, not the topic.** `day = x_schedule.ist_today()` is
  testable; `grep datetime.now()` matches the comment explaining the bug.
- **Strip comments, docstrings and string literals before grepping source.**
- **A regex containing `(` must be balanced**, or it silently under-reports.
- **A negative check needs a positive control.** `x_selfcheck.py` returned PASS on
  a file cut to 141 lines — no comment code existed because no code existed.
  Pair every "absence of X" check with a positive signal (entry point present,
  `--help` exits 0).
- **Watch for shadowed definitions after editing a test file.** Patching `t7`
  added a *second* `def t7`; Python bound the stale copy and the suite kept
  printing the old failure text, which reads as "the fix didn't work". List the
  `def` lines before concluding anything from a re-run.

## Prove the mechanism, not the outcome, when the page can't supply a sample

The `confirm()` fix had to show that Playwright passes an argument to a *bare*
function but drops it from an already-invoked IIFE. Every behavioural check
returned `None` — no matching post was on screen. That is **feed state, not
evidence about arg plumbing**, and repeating the same assertion would never
settle it.

Return `typeof h` instead of a lookup result, so the test is independent of what
the page happens to render:

```python
PROBE = """const seen = [...document.querySelectorAll('article a[href*="/status/"]')];
  return { got: typeof h, h: String(h) };"""
new = pg.evaluate("(h) => {\n" + PROBE + "\n}", "Kunalsharmadec6")   # 'string'
old = pg.evaluate("(h => {\n" + PROBE + "\n})()", "Kunalsharmadec6") # 'undefined'
```

**When the outcome is unavailable, isolate the mechanism and assert on it
directly.** A differential that proves one form passes an argument and the other
does not settles the bug even with nothing to match against. Then state plainly
that the end-to-end result was `None` and why — a blank cell reads as a defect.

Corollary: try the route that actually renders before concluding a platform
page is dead. Profile timelines returned `articles=0` while `/home` returned
articles, so a fixture-free check run against the profile proved nothing.

## Persisted randomness needs a day stamp, and a format change needs a migration

Two scheduler bugs that look unrelated and share a root: state rebuilt from
random on every tick. `build_plan()` re-rolled all 10 slot times per call, and
the due-check compared against those fresh times, so no schedule could ever be
met. Fix by persisting with an **audience-local day stamp** and loading it:

```python
data = {"day_ist": ist_day().date().isoformat(), "slots": [...]}
if data.get("day_ist") != ist_day().date().isoformat():
    return None          # stale -> rebuild, never fire at yesterday's times
```

Two traps, both hit:

- **Changing the persisted format breaks on existing files.** The old file was a
  bare list with no `day_ist`, so `data.get(...)` raised. Discard the legacy shape
  explicitly (`isinstance(data, list) -> return None`) and rebuild — never guess
  which day an unstamped plan belongs to.
- **The proof is a two-call differential.** Build twice, a second apart, and
  print both times. Identical output across calls is the evidence; "I added
  persistence" is not.

## A parser PASS is not an execution PASS

A checker can be green on code that cannot run. Built `/tmp/js_syntax_check.py`
to catch broken JS before paying a 3-minute browser round-trip: `ast`-extract
every long `=>` constant from the outreach scripts, pipe through `node --check`.
It caught a real SyntaxError, and then I used it as the gate on a file I had
just rewritten. It printed `PASS — 0 bad JS expression(s)`, and the browser
returned `Invalid regular expression: Nothing to repeat`. The file was broken.
Syntax was valid; a **runtime** `new RegExp(...)` built from a mangled escape
sequence was not.

**Know which tier your checker reaches.** `node --check`, `ast.parse`,
`tsc --noEmit` prove *shape*. They cannot see a string that parses but holds the
wrong bytes. When the thing under test is **constructed at runtime** —
`new RegExp`, `JSON.parse`, an f-string, a template interpolation — the check
must execute it:

```
node -e "new RegExp(<the literal>)"
```

**Prove every new checker can fail before trusting it.** Inject the known bug,
expect non-zero. `x_selfcheck.py` already earns this by exiting 1 when a
comment-emitting line is injected.

Same family as the section above: `python -c "import ast"` on a file whose
*scraper* was wrong reported a SyntaxError in a healthy target.

### An AST source-checker's holes are where the bugs live

`js_syntax_check.py` printed `PASS` over nine scripts and then let through the
two constructs that actually broke that session. Both holes were in the
*checker*, not the checked code:

1. It walked only `ast.Assign` targets, so a JS string passed as a **call
   argument** — `s.ev("...")` — was never checked. That is precisely the case
   that threw `SyntaxError: Illegal return statement` at runtime.
2. It required `=>` in the candidate string, so an IIFE
   (`(()=>{ ... })();`, written because `ev()` needs an expression and
   forbids a top-level `return`) has no `=>` and was skipped entirely.

And two ways a *genuinely valid* expression gets checked wrong:

3. **Implicit concatenation splits one JS expression into several Python
   `Constant`s.** Each fragment is under the length floor, so each is skipped,
   and each is invalid JS on its own. Keep such expressions as one literal.
4. **f-strings (`ast.JoinedStr`) contribute only their literal fragments** as
   `ast.Constant`, so `{CARD}[{i}]` was reconstructed as broken JS and
   reported as a failure. Rebuild with a placeholder per substitution, or skip
   `JoinedStr` explicitly.

Rule: walk every `Constant` anywhere (Assign **and** Call args), choose
candidacy markers other than `=>` (`return `, `document.`), and handle
`JoinedStr` deliberately rather than by accident.

### The checker's *file list* is the hole that costs the most

Holes 1–4 above are about parsing. The next one was about scope, and it made
every other fix theatre: the script kept a **hardcoded 13-name list** of files
to check. New scripts were never on it.

The failure was silent and I reported it as covered six times in one session.
"Adding" a file meant:

```python
s = s.replace('"li_probe_text.py"]', '"li_probe_text.py", "li_probe_close.py"]')
```

The target text was not in the file, `str.replace` returned the string
unchanged, and no error is raised — so ~18 probe files went unchecked while
every run printed `PASS — 0 bad JS string(s)`. **A whitelist you extend by
string-replace is a whitelist you will extend incorrectly at least once.**

Fix: derive the scope, don't maintain it.

```python
FILES = sorted(p.name for p in pathlib.Path(PROJECT).glob("*.py"))
```

Two related holes found in the same pass:

- **Widening scope crashes a checker that was only ever run on its own 13
  files.** The docstring walker handed a plain `str` to `ast.iter_fields` and
  raised `AttributeError`. Guard `isinstance(node, ast.AST)` at the top of any
  AST visitor — a crash mid-run leaves a partial report that reads like a
  partial pass.
- **Whole HTML pages are valid candidates and are not JavaScript.** Two
  dashboard files embed `<!doctype html>…<script>…`; markers like `document.`
  made them candidates and `node --check` reported `Unexpected token '<'` — a
  scary failure meaning nothing. Extract the `<script>` bodies and check
  those, so the real JS inside is still covered.

**And measure the checker's exit code directly.** `python3 check.py | tail -3;
echo $?` reports **`tail`'s** status, so a crashing checker printed
`GUARD_EXIT=0` above its own traceback. Run it to a file, capture the code,
then read the file:

```bash
python3 check.py > /tmp/g.txt 2>&1; echo EXIT=$?; tail -3 /tmp/g.txt
```

The round trip that proves all of it, unchanged: inject valid Python holding
invalid JavaScript → expect exit 1 → remove → expect exit 0. Proved twice over
with two *different* break shapes, so the check is not pattern-matching one
bug.

**Prove the new checker can still fail.** My first attempt injected a string
that was invalid *Python* — it died at `ast.parse` and proved nothing about
the JS path. The injection must be **valid Python holding invalid JavaScript**,
then: run, expect exit 1; restore, expect exit 0. Only that round trip shows
the check reaches the tier it claims.

## Injected JS crosses four escape layers, and four edits will not fix it

Passing a regex from Python through JS source into `RegExp` eats one level of
backslash at each hop. A `r"""..."""` with single `\d` is correct for a JS
**regex literal** and wrong for a JS **string literal**, and the reverse holds
for `\n`. Guessing produced four wrong turns, ending in a bulk replace that
**stripped all 41 backslashes** and broke the file.

**Read the actual string value instead of editing escapes again** — one `ast`
walk printing `repr()` of the constant settles in seconds what four edits
could not. Prefer a JS regex *literal* over `new RegExp`: one fewer consumer.
Full table of wrong turns: `references/js-injection-escape-levels.md`.

## Cap enforcement that counts the wrong midnight is not a cap

`runner.sent_today()` existed but was referenced **zero times**, so a 30/day
limit never applied. Wiring it in surfaced a second bug: it counted from naive
local midnight on a **UTC host**, which is 05:30 IST — miscounting most of every
day. Count from the audience's midnight:

```python
from datetime import datetime, timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))
midnight = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
```

Corollary that bit in the same pass: `grep` for the cap function name and report
the **call count**. "The function exists" is not "the cap is enforced" — a
defined-but-uncalled limiter is worse than an absent one, because it reads as
coverage in a file listing.

## Starvation that returns zero silently is the worst failure shape

A batch selector slicing `people[start : start + limit]` always takes from the
**head**. Once the head entries are spent or cooling, every tick computes an empty
batch — no error, no ledger row, exit 0. Filter the whole pool by eligibility
first, then slice:

```python
pool = load_pool()
sent = {...}
people = [p for p in pool if key(p) not in sent and not in_cooldown(p)]
batch = people[args.start_index : args.start_index + args.limit]
```

Proof is the eligible count, not the batch size: `pool=204 eligible=162
batch[0:5]=5`. A zero here is indistinguishable from success without it.

Also check **where the data lives, not just the code**: the pool was only in
`/tmp`, which `tmpfiles.d` cleans at 10 days, with no writer to regenerate it —
silent total loss on a 10-day fuse. State files under `/tmp` are a countdown.

## Report the statistic that matches the claim you are making

Two numbers from the same dataset, one defensible and one not:

- I reported **"40x"** for engagement-bait vs honest posts. That compared the
  best bait post (6,100) to the best honest post (366,000). A max-vs-max ratio
  that only exists because one 366K outlier is in the set.
- Measured properly: **median 2,450 vs 5,700 = 2.3x**. Mean 3,133 vs 36,535.

Both are true. Only the 2.3x supports "bait costs you reach." The outlier is
still real and belongs in the writeup — in the mean column, where it actually
lives, not folded into a ratio that flatters the finding.

**Before quoting a ratio, state which statistic on each side you took.** Max,
mean, and median answer different questions, and only one of them is usually the
question being asked.

Related: "word-for-word identical" for two posts measured at 0.88 similarity is
a copy with edits. Measure duplication (`difflib.SequenceMatcher` on normalised
text) rather than reading two posts side by side and recognising them.

## A correct metric with a wrong threshold is still a false finding

The sharpest form of "check the right thing": the computation can be
statistically flawless and still not measure the property you care about.
Session 2026-10-02, 23 generated post images. I computed pairwise colour
distance across all files and reported **"58 near-identical pairs out of
253"** — two genuinely different subjects, `13_confession.png` (a paper plane)
and `16_contrarian.png` (an hourglass). What my distance was actually
measuring was **shared brand palette**, which the images are *supposed* to
share. I nearly deduplicated a healthy asset library on the strength of a
metric that was correct and misnamed.

**Ask what the metric is a proxy for, before you act on a threshold.** A
threshold you invented mid-analysis has no external validation behind it.

Corollaries:

- When a cheap numeric metric flags a batch of creative work, **confirm on two
  items by eye or by inspection before touching anything.** Two confirmations
  cost seconds; a wrong "dedupe" destroys assets and is unrecoverable.
- **Self-correction is a result, not a failure to hide.** Report it plainly and
  withdraw the finding. Silently dropping the claim leaves the user believing it.
- A uniform palette across a set is usually a **brand strength**. Treat
  consistency you deliberately built as the baseline, not as the duplication
  you are hunting.

## A skill pack's guard is worth more than its prose

Before trusting a third-party posting driver, run its account check **and its
self-test**, not just the happy path. A driver that reports `"logged_in": false`
and refuses to emit is correctly refusing — the same property as a gate that can
halt. Reporting that as "not set up" invites someone to bypass it.

Three states need opposite responses:

| state | meaning |
|---|---|
| not logged in | correct refusal; sign in first |
| logged in, wrong account | **worse than not logged in** — pin the expected handle |
| logged in, right account | proceed |

Before integrating any pack that drives a browser:

1. **Grep it for the routes you did not author.** `grep -rniE "def .*(comment|reply)|reply_to|in_reply_to"` is one line and catches a posting-only violation instantly.
2. **Check for stdlib shadowing.** A `scripts/inspect.py` or `scripts/types.py`
   breaks every later import in the session. Loop every `.py` basename through
   `python3 -c "import <name>"` — one command, no false negatives.
3. **Look for an attach-to-existing-browser shortcut.** `if alive(): return True`
   makes a driver grab whatever is on its configured port. Against a port you
   did not assign it, that hijacks the session holding your real logins — and
   the pack's own README may contradict its code.
4. **Give it its own port and profile before first run.** Cheap, and it keeps
   the proof separate from the sessions that matter.

## A draft that cites competitor numbers must attribute them

Permitted **only with the method in the same sentence** — "I pulled 25 posts from
the top of this niche last month" is checkable; "7 of them opened with 'drop a
below'" is a fact we hold.

**Never adopt a competitor's number as our own metric.** The viral post built on
this reference cites the 25 / 7 / 2,450 / 5,700 set and attributes the method,
and that is the shape to copy. A number that appears in the post without a
provenance the reader could check is borrowed specificity, which is the same
failure as the pool posts it was meant to replace.

## Related

- `references/verifying-a-write-landed.md` — the four-false-negatives incident
  and a `Network.responseReceived` implementation
- `references/harvesting-competitor-posts-on-x.md` — measured route facts for
  reading X competitors: other people's profile timelines render 0 articles
  while your own renders fine, `from:<handle>` returns 0 for accounts that
  exist, topic search works; plus the three-way metadata strip (a surviving
  date silently puts a digit in every "hook") and the measured baselines
  (number in hook 3.2x, no CTA 2.7x, 250-400 chars 1.9x)
- `references/reading-conversations-on-x.md` — the "what's trending / sharpest
take each side" pass: promoted replies masquerade as the top rebuttal
(`data-testid="placementTracking"`), exact engagement lives in `aria-label`
while `innerText` is rounded (45 Likes parses as 45,000 if a `[KMB]` reader is
let loose), permalink = the `<time>` anchor, and why reply *ratio* says more
about an argument than reply count
- `references/js-injection-escape-levels.md` — the Python -> JS -> string ->
  `RegExp` backslash trap, the four wrong turns, and reading `repr()` of the
  constant instead of guessing again
- `references/scrolling-and-measuring-a-feed.md` — lazy-load scroll on a feed
  where `window` is not the scroller, why `Input.enable` must precede
  `dispatchMouseEvent`, proving the container is at its true bottom, and the
  LinkedIn route where impressions actually render
- `references/scheduled-automation-observability.md` — per-run ledgers, and
  distinguishing "ran, nothing due" from "never ran"
- `references/hosting-an-internal-dashboard.md` — serving per-action rows with
  links, X-vs-LinkedIn permalink reality, the three-case public-URL auth matrix,
  and what to state at handover
- `timezone-aware-scheduling` — audience-local windows, `OnCalendar` traps,
  and a `scripts/check_timer_window.py` probe
- `cloudflare-service-exposure` — tunnels vs A-record, and the auth-bypass trap
  when a tunnel targets the app port directly
- `linkedin-feed-engagement` — measured LinkedIn selectors; user-owned, not
  curator-editable (recommend `hermes curator adopt linkedin-feed-engagement`)
- `references/linkedin-post-menu-and-deletion.md` — removing a published post:
  a synthetic click opens an **empty** menu so the control needs real mouse
  events, the item is `DIV[role=button].feed-shared-control-menu__dropdown-item`
  not `[role=menuitem]`, the confirm is `.artdeco-modal` not `[role=dialog]`, a
  hidden modal's `aria-hidden` zeroes every later `get_by_role`, and the witness
  script must be separate from the actor
