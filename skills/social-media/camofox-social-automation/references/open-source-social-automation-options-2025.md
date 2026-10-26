# Open-source LinkedIn / X / Instagram automation options

## Status summary
- Many old scraper packages are stale or rate-limited; effectively abandoned for direct posting in 2025.
- Practical modern path: browser automation with isolated persistent profiles, not raw cookie imports per session.
- Preferred stack here: Playwright or browser-use against a working browser backend (Chrome CDP first, Camofox only if anti-detect/Firefox context is required).

## X / Twitter
- Posting directly from a logged-in browser remains more reliable than community API wrappers for account-specific behavior.
- Quirks: composer DOM is fragile; prefer JS selector-driven open over snapshot ref clicks.
- Reusable login-state backend: CDP/Playwright isolated user-data-dir per account.

## LinkedIn
- Official API still exists; for outreach/posting automation, browser automation is often used outside API allowances.
- Isolated persistent browser profile per account works better than repeated cookie imports.

## Instagram
- Official platform restrictions make fully unattended posting brittle when done through browser automation.
- Best current approach: manual/assisted flow in isolated browser profile, or platform-native scheduling/tools.

## Multi-account pattern
- Each account owns one stable profile directory.
- Launch one browser instance per account with its own `--user-data-dir`.
- Reuse `/browser connect` or Playwright context over existing profile instead of importing cookies repeatedly.
- Validate with page-state evidence, not HTTP status alone.

## Open-source project classes worth tracking
- Project names change quickly; prefer projects with recent commits and active issue triage.
- Categorize search by: `social-media-automation`, `playwright`, `browser-use`, `social-poster`.
- If a project depends on platform scraping without an official API, treat it as time-limited unless maintained.
