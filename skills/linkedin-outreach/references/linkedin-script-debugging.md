# LinkedIn Automation: Script Debugging Patterns

## Diagnostic script template

When a LinkedIn automation script fails to find UI elements (Connect button, Message button, Post button), run a standalone diagnostic before debugging the main script:

```javascript
// diag_linkedin.js — standalone probe
const http = require('http');
const USER_ID = 'linkedin_main';       // your Camofox userId
const SESSION_KEY = 'linkedin-outreach';
const BASE = 'http://localhost:9377';

function req(method, path, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(BASE + path);
    const options = {
      hostname: url.hostname, port: url.port,
      path: url.href, method,
      headers: { 'Content-Type': 'application/json' },
    };
    const r = http.request(options, (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        try { resolve(JSON.parse(d)); }
        catch { resolve({ raw: d, status: res.statusCode }); }
      });
    });
    r.on('error', reject);
    if (body) r.write(JSON.stringify(body));
    r.end();
  });
}

async function main() {
  // 1. Create tab
  const tab = await req('POST', '/tabs', {
    userId: USER_ID, sessionKey: SESSION_KEY,
    url: 'https://www.linkedin.com/'
  });
  if (!tab.tabId) { console.log('FAIL:', JSON.stringify(tab)); return; }
  console.log('Tab:', tab.tabId);

  // 2. Navigate to target
  const targetUrl = process.argv[2] || 'https://www.linkedin.com/feed/';
  await req('POST', '/tabs/' + tab.tabId + '/navigate', {
    userId: USER_ID, url: targetUrl
  });
  await new Promise(r => setTimeout(r, 5000));

  // 3. Snapshot — check URL and content
  const snap = await req('GET', '/tabs/' + tab.tabId + '/snapshot?userId=' + USER_ID);
  console.log('URL:', snap.url);
  console.log('Type:', typeof snap.snapshot);
  console.log('Len:', snap.snapshot ? snap.snapshot.length : 0);
  console.log('');
  console.log('=== AX TREE (first 3000 chars) ===');
  console.log(snap.snapshot || '(empty)');

  // 4. JS evaluate — find buttons by text
  const evalRes = await req('POST', '/tabs/' + tab.tabId + '/evaluate', {
    userId: USER_ID,
    expression: `(() => {
      const btns = document.querySelectorAll('button');
      const out = [];
      for (const b of btns) {
        const t = (b.innerText || b.textContent || '').trim();
        if (t && t.length < 50) out.push({ text: t, disabled: b.disabled, visible: b.offsetParent !== null });
      }
      return out.slice(0, 25);
    })()`
  });
  console.log('');
  console.log('=== BUTTONS FOUND ===');
  console.log(JSON.stringify(evalRes.result || evalRes, null, 2).slice(0, 1500));

  // 5. Cleanup
  await req('DELETE', '/tabs/' + tab.tabId + '?userId=' + USER_ID);
  console.log('\nDone.');
}

main().catch(e => console.error('FATAL:', e.message));
```

Run: `node diag_linkedin.js https://www.linkedin.com/in/<profile>`

## Common script bugs and fixes

### Missing `log()` function

**Symptom:** `Fatal error: log is not defined` — script crashes on first `log()` call.

**Cause:** The script calls `log(level, msg, data)` but the function was never defined. This happens when a script is written with logging calls but the definition is omitted.

**Fix:** Add the `log()` function after the HTTP helpers and before the tab lifecycle functions:

```javascript
function log(level, msg, data = {}) {
  const prefix = { info: '▸', warn: '⚠', error: '✗', debug: '·' }[level] || '·';
  const ts = new Date().toISOString().slice(11, 19);
  const extra = Object.keys(data).length ? ` ${JSON.stringify(data)}` : '';
  console.log(`[${ts}] ${prefix} ${msg}${extra}`);
}
```

Place it right after `async function del(path) {...}` and before `// ── Tab lifecycle ──`.

### Embedded null bytes in script file

**Symptom:** `read_file` reports "Binary file - cannot display as text" or Node.js crashes with vague errors like "log is not defined" (the parser chokes on null bytes before reaching any real code).

**Cause:** The script file has embedded `\x00` bytes (641 found in one case). These can be introduced by various mechanisms during file writes.

**Diagnose:**
```bash
grep -c $'\x00' script.js    # count null bytes
python3 -c "print(open('script.js','rb').read().count(b'\x00'))"
```

**Fix:**
```python
with open('script.js', 'rb') as f:
    data = f.read()
clean = data.replace(b'\x00', b'')
with open('script.js', 'wb') as f:
    f.write(clean)
```

After cleaning, verify with `node --check script.js`.

### Playwright pseudo-selectors in Firefox

**Symptom:** `page.evaluate: Document.querySelector: '.artdeco-button--primary:has-text("Connect")' is not a valid selector` — `code: "invalid_selector"`.

**Cause:** `:has-text()` and `:contains()` are Playwright-specific pseudo-selectors. They do not work with Firefox's native `document.querySelector()` or `document.querySelectorAll()`. Camofox uses Firefox's native DOM API via its REST evaluate endpoint.

**Fix:** Replace pseudo-selectors with standard `querySelectorAll` + text content matching:

```javascript
// BROKEN (Playwright pseudo-selectors):
const selectors = [
  '.artdeco-button--primary:has-text("Connect")',
  'button:contains("Connect")',
  '[aria-label*="Connect"]',
];
for (const sel of selectors) {
  const el = document.querySelector(sel);
  if (el) { el.click(); return { clicked: true }; }
}

// WORKING (standard DOM + text matching):
const buttons = document.querySelectorAll('button');
for (const btn of buttons) {
  const text = (btn.innerText || btn.textContent || '').trim();
  if (text === 'Connect' && btn.offsetParent !== null && !btn.disabled) {
    btn.click();
    return { clicked: true, selector: 'button[text=Connect]' };
  }
}
```

Apply this pattern to all button-finding code in LinkedIn scripts: Connect button, Message button, Send button, Post button, "Start a post" button.

### Snapshot return value mismatch

**Symptom:** `res.snapshot.url` is undefined, or the URL check `snap1.url.includes('/login')` fails with "Cannot read properties of undefined".

**Cause:** The Camofox snapshot response structure changed — `snapshot` field is now a string (AX tree text), and `url` is at the top level of the response object. Scripts doing `res.snapshot.url` get undefined.

**Fix:** Make the `snapshot()` function return the full response `res` instead of `res.snapshot`:

```javascript
async function snapshot() {
  if (!currentTabId) throw new Error('No active tab');
  const res = await get(`/tabs/${currentTabId}/snapshot?userId=${USER_ID}`);
  if (res.snapshot) {
    return res;  // return full response, not res.snapshot
  }
  throw new Error(`Snapshot failed: ${JSON.stringify(res)}`);
}
```

Then access `snap.url` (top-level) instead of `snap.snapshot.url`.

## Verification checklist

Before declaring a LinkedIn script "ready to run":

1. **`node --check script.js`** — syntax check passes
2. **No null bytes** — `python3 -c "print(open('script.js','rb').read().count(b'\x00'))"` returns 0
3. **`log()` defined** — grep for `function log` returns exactly one match
4. **No Playwright pseudo-selectors** — grep for `:has-text(` and `:contains(` returns no matches in evaluate JS blocks
5. **Snapshot returns full response** — `snapshot()` returns `res`, not `res.snapshot`
6. **Cookie import in main flow** — `importCookies()` called before `createTab()` in the main execution path, not just defined as a function
7. **Default tab URL is `https://www.linkedin.com/`** — not `about:blank`

## When the profile page returns a redirect loop

If the diagnostic shows "The page isn't redirecting properly" with no buttons:

- LinkedIn's anti-bot is blocking the browser profile at the network level
- This is the same class of failure as `NS_ERROR_NET_EMPTY_RESPONSE` on feed
- Clicking "Try Again" does not break the loop
- Cookie import does not fix it
- The only verified working approach is manual login in a visible Camofox browser

See `references/linkedin-anti-bot-redirect-loop.md` for the full failure analysis.
