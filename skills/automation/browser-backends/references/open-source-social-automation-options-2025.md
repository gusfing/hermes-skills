# Open-source social automation options (2025 research summary)

## X/Twitter
- Official write access via X API v2 is effectively paid-only for reliable production use in 2025; free-tier rate limits and access levels are too restrictive for posting.
- Browser automation remains the more accessible path for automated posting without API billing.
- Preferred path here: isolated Chrome profiles via CDP, not cookie-imported browser sessions.

## LinkedIn
- Some Playwright-based open-source tools exist with recent commits, but maintenance quality varies.
- Preferred fix here: do not use accessibility-ref clicks for composer or file upload when playback is inconsistent. Prefer direct browser-state interactions in an isolated profile.

## Instagram
- Instagram web composer is the most automation-hostile of the three. Expect weak ref stability and active anti-automation signals.
- If needed, prefer clean-profile manual-assisted completion over repeated unattended headless retries.

## General rule
Open-source wrappers are useful, but when a platform breaks accessible automation, the better fix is usually:
- isolated profile reuse,
- direct file-input upload,
- or manual handoff on the same stable session.

This is why the local CDP + per-account profile route became the preferred solution in this session.
