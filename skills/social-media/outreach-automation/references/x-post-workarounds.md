# X posting workarounds

## Verified working path
1. Launch Playwright Chromium with `--no-sandbox --disable-gpu`.
2. Import exported Netscape cookies into a new browser context.
3. Navigate to `https://x.com/compose/post`.
4. Use `page.focus('[data-testid="tweetTextarea_0"]')` + `page.keyboard.type(text, { delay: 40 })`.
5. Submit with JS click:
   const btn = document.querySelector('[data-testid="tweetButton"]') || document.querySelector('[data-testid="tweetButtonInline"]');
   if (btn) btn.click();
6. Verify by screenshot or profile inspection, not just redirect.

## Image upload
- `input[type="file"]` exists in the DOM even when hidden.
- `await input.setInputFiles(imagePath)` attaches media.
- After upload, type text then JS-click Post.

## Pitfalls
- Camofox keyboard input does not reach X’s React contenteditable state; Post button stays disabled.
- Playwright native click can fail because of overlay masking on composer.
- Direct X API needs bearer token + CSRF token; without them, 401/403 is expected.
- Duplicate content may return a success-looking flow with an error toast. Use unique text or direct profile check for proof.
- Playwright/headless Chromium user agent must be spoofed to a normal Chrome UA or WhatsApp shows the browser-compatibility warning page.
