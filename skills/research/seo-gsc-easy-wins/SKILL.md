---
name: seo-gsc-easy-wins
description: Use when mining Search Console for page-two keywords.
---

# SEO Search Console Easy Wins

Converts near-misses into drafts. Positions 11-13 are the cheapest wins
available: the page is already indexed and Google already respects it, it just
isn't beating 10 competitors yet.

## Why 11-13 specifically

Top-10 pages are what AI answer engines cite. Moving a position-12 keyword to
page one feeds **two channels at once** — Google traffic and AI citations. That
double payoff is why this skill exists rather than a generic "write more posts".

## BLOCKING PREREQUISITE

**This skill cannot run until Search Console credentials exist.** Verified absent
on this machine (no `~/.credentials/*search-console*`, no GSC creds anywhere).
Verify before promising anything:

```bash
ls ~/.credentials/search-console*.json ~/.gsc/*.json 2>/dev/null
```

No file → **stop.** Report that GSC is not configured. Do not fabricate rankings,
do not substitute a third-party traffic estimate, do not guess which keywords the
site ranks for. Fabricated rank data is worse than no skill.

Ask the user for the service-account JSON path or the OAuth client
credentials. Never ask them to paste a private key into chat — see the
`session-paste-security` skill. Have them drop the file on disk and tell you the
path.

## Procedure (once credentials exist)

1. **List properties** and confirm which one the user means. Multiple properties
   is normal; ask, don't pick the first.
2. **Pull queries, last 90 days.** Positions 11-13 only:
   - `page`, `query`, `position`, `clicks`, `impressions`
   - Sort by `impressions` desc — high impressions + position 11-13 means real
     demand sitting just out of reach.
4. **Filter to actionable ones.** Reject a query if:
   - the ranking page is already the best answer for a different intent
   - the SERP intent doesn't match the existing page (informational vs commercial)
   - the page is already on page one for a cluster of near-identical queries
5. **Draft for the top 3.** Vault-first — read past writing and offers before
   drafting. See `seo-vault-voice`.
6. **Output the plan:**

```
QUERY: <query>
POSITION: 11.3  (avg over 90d)
IMPRESSIONS: 4,120  CLICKS: 38
PAGE: <url>
GAP: <why it isn't ranking — thin content, missing section, no internal links, wrong intent>
TARGET TITLE: ...
TARGET H1: ...
SECTIONS TO ADD: <bullet list>
```

## Hard rules

- **Never invent position, impression, or click numbers.** Every number must
  come from the API response in this run.
- **90 days, not 7.** Short windows are noise. A position 12 on a 40-click
  query is not an opportunity.
- **One page per query.** If two queries need the same page, that's one task.
- **Drafts go to `drafts/`, never straight to publish.** Review is the user's call.
