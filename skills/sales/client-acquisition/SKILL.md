---
name: client-acquisition
description: "Outbound sales: email, LinkedIn, sequences, pipeline."
---

# Client Acquisition

Use when the user wants to get clients, book meetings, run outbound sales, send outreach emails/LinkedIn messages, or build a sales kit for a venture. Covers lead generation, sequencing, templates, SMTP sending, and pipeline tracking.

## Trigger
- "get clients", "book meetings", "outreach", "cold email", "LinkedIn outreach"
- "sales kit", "proposal", "lead list", "pipeline", "schedule a meet"
- Any request to build outreach assets for a studio/agency/brand

## Approach
Be direct and action-first. Do not explain why outreach works; just build the kit and ask for credentials/channel. Default output:
1. `templates/` — cold email, LinkedIn, call script, proposal, follow-ups
2. `sequences/` — 3/5/7-touch cadences
3. `tracking/` — lead tracker CSV, pipeline board, KPI dashboard
4. `scripts/send_email.py` — SMTP batch sender

## Execution Steps
1. Confirm niche/service and ideal client profile in one message.
2. Create the sales kit folder with templates, sequences, tracking.
3. Ask for SMTP provider + sending address.
4. Write `email/config.yaml` and `email/send_email.py`.
5. Send a self-test to the user's own address.
6. Provide exact CLI commands for single/batch send.

## Ramped caps, and stating the risk once

When a user asks to raise a daily send volume, do not just set the number. A new
account on an unofficial/automated client (WhatsApp via `whatsapp-web.js`, cold
email on a fresh domain) can be banned outright — a ban is a dead asset, not a
warning. So:

1. **Say the risk in one sentence, then do what they decide.** No moralizing, and
   never silently apply a lower cap than requested — a hidden override is worse
   than disagreeing, because the user cannot see it happening. Use a clarifying
   question with the risk stated in it, offer a concrete ramp as the first
   choice, and accept their call.
2. **Implement the ramp rather than a flat number.** Date-anchored, not
   "N days after first run", so every machine and every report reads the same.
   Route all callers through one `cap_for(channel, now)` — the moment one
   caller reads the raw config dict, the ramp silently does not apply and the
   symptom reads as "the ramp isn't working" instead of a bypass.
3. **Assert the boundary, not just the direction.** A check that only proves
   "it goes up later" passes happily when the off-by-one doubles the intended
   volume on the ramp day. Test day zero, mid-warmup, the last warmup day, the
   first ramp day, and one channel that must never ramp.
4. **Prefer filtering over volume where a filter exists.** A per-recipient
   "is this even a real account" check turns a spray list into real
   conversations, so a modest cap goes further. Cap the check pass too — bulk
   validating a whole list is itself the pattern the cap exists to prevent.
5. **Print ramp state in the daily report** (`day 0/14, 14 more at 15/day`) so it
   is visible without opening a file.

## The local cap is a rail, not the platform's limit

A cap in `config.py` is your own safety rail. It is not what the platform
allows, and the two drift apart silently. A config reading 30/day next to a
real quota of 3/month is worse than publishing no number at all — it is a wrong
number, and the user will build a plan on it.

So: read the real allowance from the platform at send time, report both, and
name which is which. When they disagree, say so and recommend lowering the
local one. Never quote a volume from config alone.

## One exhausted path is not a dead end

A quota blocking one route usually does not block the cheaper variants of it.
Observed on LinkedIn: the 3-per-month allowance covers **personalized notes**,
while the no-note invite path sits on a separate and much larger budget. The
right response to an exhausted allowance is therefore *not* "you are done".

Before declaring a channel spent, enumerate the variants that carry a separate
budget — with/without a note, post vs DM vs reply, follow vs message — and test
the cheapest one.

Then state the tradeoff instead of hiding it. Un-noted invites are dispatched
but accepted far less often, and on the one real run **both inbound replies
came from people who had received a personalized note**. Give the user the
choice with the cost visible, rather than a false either/or.

## Replies beat the sends that produced them

Inbound is the highest-value state in an outreach pipeline and the one least
likely to be checked. On that run, two people replied with substantive
questions while 27 blank invites produced nothing measurable.

- Check the inbox before spending the day's budget.
- Report replies by their actual questions, not a count.
- Offer to draft the answers first. That is a smaller task with a much higher
  return than another batch.

## Prove one send before a batch, and verify it independently

Dry-run by default, explicit flag to send. Before any batch: run the plan,
prove one send end to end, then verify it against a control that was not sent
to. A batch launched on the strength of a dry run alone is a bet.

Control-based verification is what makes it evidence rather than inference — an
invited person loses their invite control while an untouched one keeps it. The
same trick applies wherever "did it actually go out" is in question and a
no-op is indistinguishable from a failure.

## Pitfalls
- Do not iterate templates without user input; send raw v1 and ask for one specific edit.
- Do not use HTML by default; plain-text is safer for cold outreach.
- Do not send batch campaigns before user confirms daily limit and list quality.
- Do not put credentials in repo; ensure `.gitignore` covers `email/config.yaml`.
- Do not gate a no-copy mode behind a "skip anyone without a message" rule.
  That rule is right for personalized sends and quietly drops exactly the
  people a no-copy run should still reach — and it fails silently, so the run
  looks healthy while quietly sending fewer. Branch on the mode *before* the
  draft gate and log what each gate excluded.
- Do not let the send path read targets from anywhere but the state store. A
  run that sends from a side file leaves the DB claiming zero sends, and the
  two records then disagree irreconcilably.
- If user says "stop explaining" or "just give me the answer", drop rationale and give the artifact/command.

## References
- `references/outreach-metrics.md` — reply rate benchmarks by channel
- `references/smtp-providers.md` — provider-specific SMTP settings
- `linkedin-outreach` skill — LinkedIn invite DOM path, the 3/month
  personalized-note quota, and the no-note path that bypasses it
- `cold-outreach-pipeline` skill — queue/cooldown/clock-seam build order

## Templates
- `templates/email-cold-v1.md`
- `templates/linkedin-cold-v1.md`
- `templates/call-script.md`
- `templates/proposal-v1.md`
- `templates/followup-v1.md`

## Sequences
- `sequences/3touch.md`
- `sequences/5touch.md`
- `sequences/7touch.md`

## Scripts
- `scripts/send_email.py`
