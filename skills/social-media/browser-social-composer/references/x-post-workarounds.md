# X/Twitter and WhatsApp posting workarounds session notes

## X verified workflow
- Exported Netscape cookies with `auth_token` + `ct0` + `.x.com`/`x.com` entries are sufficient.
- Playwright Chromium with `--no-sandbox --disable-gpu` and a real Chrome UA string.
- `page.focus('[data-testid="tweetTextarea_0"]')` + `page.keyboard.type(text, {delay: 40})`.
- Submit via `page.evaluate(() => { const btn = document.querySelector('[data-testid="tweetButton"]') || document.querySelector('[data-testid="tweetButtonInline"]'); if (btn) btn.click(); })`.
- Success = redirect to `/home`, success toast, or exact post text on `[data-testid="tweetText"]` in profile scan.

## X image posts
- Locate `input[type="file"]` and call `await input.setInputFiles(absolutePath)` before submit.
- PNG/JPG supported. If upload silently fails, retry once with same path.

## X duplicate content limit
- X returns “Whoops! You already said that.” for reused text.
- Use unique text per attempt to disambiguate from earlier posts.

## Hard stop signals
- Direct X HTTPS API calls blocked by command approval policy in terminal heredoc.
- Direct X v2 API returns 401 without bearer token.
- CDP `Runtime.evaluate` unavailable on some backends.
- `browser_click` unverifiable on masked composer.
- Do not loop same submit without changed condition.

## WhatsApp persistent-context
- WhatsApp Web rejects default Playwright/HeadlessChrome UA.
- Set UA before navigation: `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36`.
- Launch with `chromium.launchPersistentContext(profileDir, { executablePath, args: ['--no-sandbox','--disable-gpu'], headless: true, userAgent: <above> })`.
- Loading screen ≠ QR code ≠ logged-in. Treat as three distinct states.
- If snapshots/vision repeatedly timeout, fall back to Playwright persistent context instead of looping on CDP.

## WhatsApp QR dashboard
- Host an isolated Node dashboard on an unused port, e.g. 3001.
- The `/api/wa/start` handler must return immediately.
- Launch QR capture in a detached `child_process.fork` so it does not block the HTTP response.
- Capture QR by screenshotting the `canvas` element on `https://web.whatsapp.com`.

## Why Camofox composer failed
- Camofox `click` + `type` reached the DOM, but the post button stayed disabled.
- A layers overlay intercepted pointer events on `[data-testid="tweetTextarea_0"]`.
- Synthetic events did not sync to X's React composer state.
