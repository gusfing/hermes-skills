const http = require('http');
const WebSocket = require('ws');

const TAB_ID = process.argv[2] || 'unknown';
const USER_ID = process.argv[3] || 'x_account_a';
const API = 'http://127.0.0.1:9377';

function httpRequest(path) {
  return new Promise((resolve, reject) => {
    http.get(API + path, (res) => {
      let data = '';
      res.on('data', (c) => data += c);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error('Non-JSON: ' + data.slice(0, 100))); }
      });
    }).on('error', reject);
  });
}

(async () => {
  // Step 1: Get tab snapshot
  const snap = await httpRequest(`/tabs/${TAB_ID}/snapshot?userId=${USER_ID}`);
  console.log('Current URL:', snap.url);
  
  // Step 2: Try JS opener for composer
  const wsUrl = `ws://127.0.0.1:9377/devtools/page/${TAB_ID}`;
  const ws = new WebSocket(wsUrl);
  
  ws.on('open', () => {
    const js = `(() => {
      const candidates = Array.from(document.querySelectorAll('[data-testid="tweetTextarea_0"], [href="/compose/post"], [data-testid="SideNav_NewTweet_Button"], a[href="/compose/post"]'));
      const el = candidates.find(e => e.offsetParent !== null || e.tagName === 'A');
      if (!el) return 'no_candidate';
      el.click();
      return 'clicked';
    })()`;
    
    ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: { expression: js, returnByValue: true } }));
  });
  
  ws.on('message', (raw) => {
    const data = JSON.parse(raw.toString());
    if (data.id === 1) {
      const result = data.result?.result?.value || data.result || {};
      console.log('JS opener result:', result);
      ws.close();
      process.exit(0);
    }
  });
  
  ws.on('error', (err) => {
    console.error('WS error:', err.message);
    process.exit(1);
  });
  
  setTimeout(() => {
    console.error('timeout');
    ws.close();
    process.exit(1);
  }, 15000);
})();
