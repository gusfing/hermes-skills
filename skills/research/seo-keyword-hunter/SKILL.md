---
name: seo-keyword-hunter
description: Use when finding SEO keywords or content angles for a niche.
---

# SEO Keyword Hunter (Astros pattern)

Standing keyword patrol. You keep the keyword list; the skill watches it forever.

## The keyword list lives IN this file

Edit the `KEYWORDS` block below. That is the whole configuration — no external
tool, no stale CSV export. Each run patrols these terms.

```
KEYWORDS:
- <term>
- <term>
```

`ponytail:` no search-volume data source is wired. Volume/intent comes from
live SERP shape (see below), not a Semrush export. Add a real volume API only
once ranking decisions depend on volume, not on which queries return results.

## Procedure

1. **Read the list.** If `KEYWORDS` is still the placeholder above, stop and
   ask the user for their terms. Do not invent keywords.
2. **Search each term** with `web_search`. One pass per term.
3. **Read the shape of the SERP, not just the ranks.** For each term record:
   - `results`: total distinct URLs returned
   - `forum_hits`: results on Reddit / Stack Overflow / Quora / a niche forum
   - `date_freshness`: how recent the top results are
   - `weak_pages`: pages that look thin, generic, or obviously AI-written
4. **Classify intent** from SERP shape:
   - Forums dominating → people ask questions, not shopping. Write an answer-first post.
   - Listicles / "best of" dominating → comparison intent. Write a ranked piece.
   - All vendor pages → commercial intent. Write a buyer's-guide or comparison.
   - Mostly stale dates → freshness gap. Write an updated, current piece.
5. **Turn each term into one content idea.** Output:
   - `term`, `intent`, `angle`, `suggested_title`, `why_now`
   - `difficulty`: LOW / MED / HIGH from SERP shape only. Never quote a number
     you did not measure.
6. **Rank ideas by `why_now` strength.** Prefer a gap you can name (stale
   results, thin pages, unanswered forum question) over a generic high-volume term.

## Output

```
TERM: <term>
INTENT: <answer | comparison | commercial | freshness>
ANGLE: <one line>
TITLE: <suggested title>
WHY NOW: <the specific gap you observed, with evidence>
DIFFICULTY: LOW|MED|HIGH (from SERP shape)
```

## Hard rules

- **No volume or difficulty numbers you did not measure.** Describe the SERP,
  not a metric from memory.
- **Every idea cites the observed gap.** "High volume" is not a gap.
- **Read the vault first** if drafting follows — see `seo-vault-voice`.
- **One idea per term per run.** No padding.
