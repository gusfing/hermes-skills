---
name: seo-winner-analyst
description: Use when ranking your own content to forge next ideas.
---

# SEO Winner Analyst (Muse pattern)

Oracle tells you what the world cares about. Muse tells you what your audience
has already voted for.

## The rule that matters: climb speed beats raw size

A video sprinting on day one outranks one coasting on old momentum. Rank by
**velocity**, not absolute numbers. A 50k-view video from eight months ago is
decayed inventory; a 3k-view video from three days ago is a signal.

## Data sources, in order of preference

Check what's actually wired before promising analysis:

1. **`references/channels.md`** — edit this file with your own channel URLs.
   Without it this skill has nothing to read.
2. **Available tools** — if `youtube-content` skill is available, use it for
   transcript-backed titles. Check `skills_list` before claiming you can't.
3. **Ask.** If neither exists, ask for the last 20 published pieces with their
   view counts and dates. Do not guess at performance data.

`ponytail:` no analytics API is wired. This skill ranks whatever numbers you
give it. Add a real analytics source before trusting it on a large catalog.

## Procedure

1. **Gather** the last 20-30 pieces: title, format, publish date, views at 7
   days and now (if only "now" is available, use it and say so).
2. **Compute climb speed** where both numbers exist: `(now - at_7d) / max(days_since_publish, 1)`.
   Rank desc. Flag any piece still climbing at 30+ days.
3. **Extract patterns from the top 5** only. Patterns from the bottom half are
   noise. Look for:
   - title structure (question / number / contrarian / how-to / named entity)
   - hook length — what does the first line do
   - format (short vs long, video vs text)
   - whether the top pieces answered a question or made a claim
4. **Forge ideas** riding those patterns. Titles in the proven style, each with
   a `confidence` score derived from the pattern's hit rate:

```
PATTERN: <what the winners share>
HIT RATE: 4 of 5 top pieces
IDEA: <title>
CONFIDENCE: 0.8  (why: pattern hit 4/5 in last 30 days)
ROUTE: video | article | image
```

## Hard rules

- **Only real numbers.** If views aren't provided, don't invent them or rank by
   impression. Ask.
- **Rank by velocity when velocity data exists.** Say which basis you used.
- **Patterns from winners only.** Never generalise from what flopped.
- **Confidence must trace to a counted pattern**, not a feeling.
