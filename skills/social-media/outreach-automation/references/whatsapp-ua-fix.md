# WhatsApp UA fix

## Failure mode
Loading `https://web.whatsapp.com` with Playwright/headless Chromium shows the browser-compatibility warning page: "WhatsApp works with Google Chrome 100+". This happens because WhatsApp detects HeadlessChrome or an outdated UA string.

## Fix
Spoof a normal desktop Chrome UA when launching Playwright persistent context:

```js
const context = await chromium.launchPersistentContext('/path/to/wa-profile', {
  executablePath: '/path/to/chrome',
  args: ['--no-sandbox','--disable-gpu'],
  headless: true,
  userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'
});
```

## Loading states
- After UA fix, WhatsApp may show a loading screen for several seconds before chats appear.
- Do not confuse loading screen, QR login screen, and chat list. Each requires different next steps.
- If only the loading screen is visible, wait longer before asserting logged-in state.

## Input selectors after load
Use this priority:
1. `[contenteditable="true"][data-tab="10"]`
2. `#main footer div[contenteditable="true"]`
3. `footer div[contenteditable="true"]`

Send messages with Enter key, not by clicking Send.

## QR capture for dashboard
- The QR canvas selector `canvas` should be present on `https://web.whatsapp.com` when user is not logged in.
- Screenshot the canvas and serve it via `/public/qr.png`.
- Refresh QR by re-running the WhatsApp start flow and overwriting the saved PNG.
