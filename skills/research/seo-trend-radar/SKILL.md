---
name: seo-trend-radar
description: Use when hunting niche trends to publish fast.
---

# SEO Trend Radar (Oracle pattern)

Morning news radar. Ranked by audience relevance first, freshness second.

## The hard number: SIX signals

**Six. Not a firehose.** A radar that returns forty links is a radar nobody
reads. If more than six things qualify, you ranked wrong. Cut to six.

If the user asks for a different count, honour it — but say plainly that the
six-signal discipline is the reason this skill works and their number loses that
guarantee.

## Procedure

1. **Read the niche from `references/niche.md`**, or ask for it. Never guess the
   niche — a generic radar is a generic feed.
2. **Two to three `web_search` passes** with different query shapes:
   - `<niche> news`, `<niche> announcement`, `<niche> launch`
   - recency-biased phrasing; prefer results with dates
3. **Rank by audience relevance FIRST, freshness second.** A two-week-old story
   that directly hits the niche beats a two-hour-old story from an adjacent
   field. This ordering is the whole point of the skill.
4. **Cut to exactly six.** For each, produce:
   - `headline` — the actual news, not a paraphrase
   - `why_trending` — the specific trigger, not "it's popular"
   - `content_angle` — what this site would say about it
   - `opening_line` — a first sentence the user could post verbatim
   - `source_url` — **required.** No source, no signal.
5. **Flag coverage.** If the niche is already saturated on this story, mark it
   `SATURATED — skip` and replace it with the next candidate. Being late on a
   covered story wastes the slot.

## Output

```
1. HEADLINE: ...
   WHY TRENDING: <specific trigger>
   ANGLE: <our take>
   OPENING LINE: "..."
   SOURCE: <url>
   STATUS: FRESH | SATURATED — skip
```

## Hard rules

- **Six signals or fewer.** Enforce it even when more qualify.
- **Relevance beats recency** in the ranking. Do not sort by date.
- **Source URL is mandatory** for every signal.
- **Never fabricate a headline** to fill a slot. Fewer than six is a valid
  result; say how many qualified and why the rest were cut.
- **Today's date is a tool fact, not a memory fact.** Query the current date
  before judging whether something is fresh. Servers lie about their own clock.
