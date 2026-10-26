# LinkedIn CLI Tools — HTTP-based approaches (tested 2026-08-31, updated 2026-09-01)

## Finding

LinkedIn CLI tools that make direct HTTP requests (not browser automation) hit LinkedIn's anti-bot wall. This is a different failure mode from browser fingerprinting, but the same outcome: blocked for most endpoints. However, the `identity/me` Voyager endpoint can work **intermittently** from a flagged Oracle Cloud IP with fresh cookies.

## Tools tested

| Tool | Install | Auth | Result |
|---|---|---|---|
| `@bcharleson/linkedincli` (npm: `@bcharleson/linkedincli`) | `npm i -g @bcharleson/linkedincli` | Cookie paste or env vars (`LINKEDIN_LI_AT`, `LINKEDIN_JSESSIONID`) | Auth accepted. `profile me` returned real profile data **once** with fresh cookies (2026-09-01), but search/feed/connections timeout. `identity/me` Voyager endpoint can work intermittently — other endpoints (feed, search, connections, profile view of others) are blocked (302 or timeout). |
| `lxgicstudios/linkedin-cli` (npm: `linkedin-cli`) | `npm i -g linkedin-cli` | `--cookie <li_at>` / `--csrf <JSESSIONID>` | Auth saves OK, calls fail with `fetch failed` |
| `@linkedapi/linkedin-cli` (npm: `@linkedapi/linkedin-cli`) | `npm i -g @linkedapi/linkedin-cli` | Token-based (their proxy) | Not tested — install conflicts with existing `linkedin` binary |
| `@lucasygu/lockedout` (npm: `@lucasygu/lockedout`) | `npm i -g @lucasygu/lockedout` | Requires `lockedout login` (real Chromium via Patchright) | Installed v0.3.3. `lockedout doctor` checks: Node 22, Patchright 1.62.2, Chromium cached at `~/.cache/ms-playwright`. Needs a real Chromium profile from `lockedout login` — cookies file alone (`~/.lockedout/cookies.json`) is not enough. Two paths to create profile: (a) remote display/Xvfb + manual login, or (b) headless cookie-seed via Patchright (tested — Chromium launches and cookies inject, but LinkedIn serves 39-byte blank page — fingerprint still detected). |

## Config paths

Different tools store config in different places:

- `@bcharleson/linkedincli`: `~/.linkedin-cli/config.json`
  - Reads `config.li_at` and `config.jsessionid` (lowercase j)
  - Does NOT read `config.JSESSIONID` (uppercase) — that's a common misconfiguration
  - Status command: `linkedin status` → returns `{"logged_in":true}` when cookies are present
  - The tool introspects its own config path, so writing to the right file matters

- `lxgicstudios/linkedin-cli`: uses `conf` package (default config dir)
  - Auth via `linkedin-cli auth --cookie <li_at>` (interactive prompt in v1.0.0)
  - Non-interactive auth may not work — tool expects stdin for cookie paste

- `@lucasygu/lockedout`: `~/.lockedout/` directory
  - `cookies.json` — cookie store (29 cookies from fresh LinkedIn export)
  - `profile/` — Chromium profile dir (created by `lockedout login`, NOT by cookie import)
  - `config.json` — tool config
  - `lockedout doctor` checks: Node.js version, Patchright, Chromium cache, profile dir, session, quota, cooldown, activity hours

## Fresh cookies (2026-09-01)

29 LinkedIn cookies shared and imported on 2026-09-01. Key fields:

- `li_at`: `AQEDATczB7cDPjhhAAABoF5TQZMAAAGggl_Fk00A0u-qj_-dBq2cmvBLZ-3TaWDXlAt_ZJoZctLYOKStlmMtr6_prOjmvhqR6fQQnZhUJbmttdU7L2GFq_germb8pgaucT91M6ko1zZIGIHi1F44jmew`
- `JSESSIONID`: `ajax:326139612517357081`
- Plus: `li_sugr`, `bcookie`, `bscookie`, `g_state`, `_guid`, `aam_uuid`, `li_theme`, `li_theme_set`, `dfpfpt`, `visit`, `li_rm`, `s_fid`, `mbox`, `gpv_pn`, `s_ips`, `s_tslv`, `s_tp`, `AMCV_*`, `lang`, `timezone`, `lms_ads`, `lms_analytics`, `UserMatchHistory`, `AnalyticsSyncHistory`, `liap`, `lidc`, `sdui_ver`

These fresh cookies were written to both `~/.linkedin-cli/config.json` and `~/.lockedout/cookies.json`. `linkedin-cli profile me` returned real profile data once (Kunal's profile: plainId `926091191`, publicIdentifier `kunal-sharma-webdev`), but subsequent calls timed out. This suggests the `identity/me` endpoint is sometimes accessible from this Oracle Cloud IP while other endpoints remain blocked.

## What failed and why

**Most tools**: cookies are accepted by the CLI tool's local config, but most HTTP requests to `www.linkedin.com/voyager/api/...` return empty or time out.

**Root cause (IP-level, selective):** Direct `curl` tests from this Oracle Cloud box confirm:
- `curl -I https://www.linkedin.com` → HTTP 200 (homepage HTML loads)
- `curl -H "Cookie: li_at=...; JSESSIONID=..."` to Voyager API `identity/me` → **sometimes works** (returns profile JSON), sometimes 302
- `curl` to Voyager API `feed`, `search`, `connections` → HTTP **302** redirect (session invalidated)
- `curl` to public profile without cookies → HTTP **999** (LinkedIn's bot-block)
- `curl` to feed with cookies → HTTP **302** redirect (session invalidated)

The Oracle Cloud IP is flagged by LinkedIn, but the blocking is **selective** — `identity/me` can work intermittently while other endpoints are consistently blocked. Browser fingerprint is NOT the only factor — the IP itself is blocked at the API level for most endpoints.

## What does NOT work

- Cookie-based CLI tools against LinkedIn from a blocked IP for most endpoints (feed, search, connections, profile view of others)
- Any HTTP-based approach from this Oracle Cloud instance for most authenticated endpoints
- Installing `@linkedapi/linkedin-cli` over `@bcharleson/linkedincli` without renaming the binary first (both claim `linkedin` in `bin`)
- `lockedout` cookie file alone — needs real Chromium profile from `lockedout login`
- Headless Chromium (Patchright) with injected cookies — LinkedIn serves 39-byte blank page

## When CLI tools MIGHT work

- `profile me` (`identity/me` endpoint) can work intermittently from this Oracle Cloud IP with fresh cookies
- From a non-blocked IP (different cloud provider, residential IP, or a VPS LinkedIn hasn't flagged)
- With fresh cookies from a real browser login (current cookies were fresh on 2026-09-01 and `profile me` worked once)
- `@linkedapi/linkedin-cli` routes through their proxy — different exit IP, might bypass. Untested.
- `@lucasygu/lockedout` with a manually logged-in Chromium profile on a non-blocked machine

## Install conflict

Both `@bcharleson/linkedincli` and `@linkedapi/linkedin-cli` install a binary named `linkedin` to the same global bin dir. Installing the second fails with `EEXIST`. To test both:
```bash
mv $(which linkedin) /home/opc/.local/bin/linkedin-bcharleson
npm i -g @linkedapi/linkedin-cli
# Now `linkedin` is the @linkedapi version, `linkedin-bcharleson` is the other
```

## Cookie sharing workflow (2026-09-01)

User can share LinkedIn cookies directly (paste the Netscape cookie string). The agent:
1. Parses the cookie string into structured objects
2. Writes `cookies.json` to `~/.lockedout/` (for lockedout) AND `config.json` to `~/.linkedin-cli/` (for linkedin-cli)
3. Must use `sameSite: "None"` (capital N) for Patchright compatibility — lowercase `"none"` causes `addCookies` to reject with `expected one of (Strict|Lax|None)`
4. Verifies with `linkedin status` and `linkedin profile me`

Full cookie set from a fresh LinkedIn browser session should include at minimum: `li_at`, `JSESSIONID`, `bscookie`, `bcookie`, `li_sugr`, `li_rm`, `lidc`, `liap`, `lang`, `g_state`, `_guid`, `aam_uuid`, `li_theme`, `li_theme_set`, `dfpfpt`, `visit`, `s_fid`, `mbox`, `timezone`, `sdui_ver`. More cookies = more reliable.

## lockedout + Patchright approach

`@lucasygu/lockedout` is a LinkedIn CLI that drives real Chromium via Patchright (a Playwright fork with stealth patches). Unlike HTTP-based CLI tools, it uses a real browser — but still needs a manually created Chromium profile.

**Setup:**
```bash
npm install -g @lucasygu/lockedout
lockedout doctor   # verify Node, Patchright, Chromium
```

**Creating a session (two paths):**

Path A — Remote display + manual login:
1. Set up Xvfb or VNC on the server
2. Run `lockedout login` — opens Chromium, user manually signs in to LinkedIn
3. After sign-in, `lockedout status --verify` confirms the session
4. Then `lockedout profile <username>` works headlessly

Path B — Headless cookie-seed (untested effectiveness):
1. Write cookies to `~/.lockedout/cookies.json` (use `sameSite: "None"` capital N)
2. Write a Patchright script that launches headless Chromium, calls `context.addCookies(cookies)`, then navigates
3. Test with Voyager API fetch from within the page context
4. Known result: Chromium launches, cookies inject, LinkedIn homepage loads — but serves 39-byte blank page (fingerprint still detected)

**lockedout commands:**
- `lockedout doctor` — environment check
- `lockedout login` — create Chromium profile via manual login
- `lockedout status` — check session state
- `lockedout status --verify` — verify session against LinkedIn
- `lockedout profile <username>` — look up a profile
- `lockedout usage` — check quota/limits
- `lockedout logout` — clear session

**Pitfall:** `lockedout` is NOT a cookie-import tool. It does not read `cookies.json` to create a session. It needs a real Chromium profile directory at `~/.lockedout/profile/` created by `lockedout login`. The `cookies.json` file is only used as a recovery/export artifact, not as a session bootstrap.
