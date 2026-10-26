---
name: github-recon
title: GitHub Repository Research
description: 'Research, audit, and evaluate GitHub repositories: discover active projects, verify
  stack/liveness, and extract actionable metadata without relying on unavailable browser/search
  tools. Use when the user asks to find GitHub repos, evaluate OSS tools, check if a project
  is maintained, or compare automation/social/discord/ai projects on GitHub.'
triggers:
  - find github repos for
  - research github projects
  - evaluate open source tools on github
  - check if github project is maintained
  - find active github repositories for
  - github alternatives for
---

# GitHub Repository Research

## Goal
Rapidly identify, rank, and verify GitHub-hosted open-source solutions for a class of tools
(e.g., social auto-posters, browser automation, integrations) and report concrete evidence
about liveness, stack, and whether they still work.

## When to use
- The user asks to research GitHub options for a platform, library class, or workflow.
- You must distinguish actively-maintained projects from abandoned ones.
- Browser and web search are unavailable or blocked; you still need reliable results.

## Default workflow

### 1. Candidate discovery via GitHub search HTML
```bash
curl -sL "https://github.com/search?q=<KEYWORDS>&type=repositories&s=stars&o=desc" \
  | grep -oE 'href="/[^"]+/[^"]+"' \
  | grep -v '/topics/' | grep -v '/search/' | sort -u
```
- Adjust keywords: include the platform and automation verbs (`linkedin auto post playwright`,
  `twitter x post playwright`, `instagram auto post`).
- Add `filetype` style filters only if needed; GitHub HTML search is sufficient for star-ranked
  discovery.

### 2. Metadata verification via GitHub API
For each candidate repo:
```bash
curl -sL "https://api.github.com/repos/<OWNER>/<REPO>" | jq '{full_name, stargazers_count, forks_count, updated_at, pushed_at, language, description, html_url}'
```
Key fields:
- `pushed_at` reflects true code activity; `updated_at` reflects metadata bumps.
- `language` confirms stack claims.
- Low stars + recent pushes can still indicate small but alive projects.

### 3. README and dependency inspection
```bash
curl -sL "https://raw.githubusercontent.com/<OWNER>/<REPO>/main/README.md" | head -n 120
curl -sL "https://raw.githubusercontent.com/<OWNER>/<REREPO>/main/package.json" | head -n 40
curl -sL "https://raw.githubusercontent.com/<OWNER>/<REPO>/main/requirements.txt" | head -n 40
```
- Inspect dependencies to validate stack claims (Playwright, Selenium, instagrapi, tweepy, etc.).
- Read setup instructions to infer whether the project is runnable in 2025.

### 4. Multi-account isolation and compatibility heuristics
When the user cares about multi-account isolation, look for explicit evidence:
- Separate browser profiles or session directories
- OAuth client credentials per instance
- Per-account `.env` or config files
- Runtime account switching

Absent explicit docs, state the likely isolation level honestly rather than guessing.

### 5. Reporting format
Return structured findings per platform:
- Repo name, stars, last push date
- Stack/language
- Multi-account support status
- Likely functional status in 2025
- Link

## Pitfalls
- `github.com/search` HTML and API rate limits: throttle if doing bulk checks; stagger requests.
- Automatic branch may be `master`, not `main`. Try both paths if the first returns 404.
- `language: null` on GitHub API can mean a repo of config/JSON-only files; verify with raw README.
- GitHub Actions integrations may show recent `updated_at` even if core code is stale.
- X/Twitter writing via official API now effectively requires paid access; browser-automation tools
  are preferable for free automation.
- Instagram private API clients (`instagrapi` and variants) are functional and actively maintained
  but carry TOS risk.

## Workarounds
- If `web_search` fails (e.g., missing `ddgs` package), do not repeat it blindly. Go directly to
  GitHub HTML search and the GitHub REST API via `curl`.
- If `browser_navigate` connects to camofox but fails, drop to terminal-based discovery. Browser
  automation is a convenience layer, not a prerequisite for repo research.
