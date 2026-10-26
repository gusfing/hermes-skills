#!/usr/bin/env node
/**
 * Camofox REST API debug probe
 * Tests the core workflow: create tab, navigate, snapshot
 * Use this to diagnose whether a script failure is in the API calls
 * or in the page interaction logic.
 *
 * Usage: node camofox-probe.js
 */

const http = require('http');

const CAMOFOX_URL = process.env.CAMOFOX_URL || 'http://localhost:9377';
const USER_ID = process.env.USER_ID || 'test';
const SESSION_KEY = process.env.SESSION_KEY || 'probe';
const TEST_URL = process.env.TEST_URL || 'https://www.linkedin.com/feed/';

function request(method, path, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(CAMOFOX_URL + path);
    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.href,  // ← must include query params
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (c) => (data += c));
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch { resolve({ raw: data, status: res.statusCode }); }
      });
    });
    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

async function probe() {
  console.log(`=== Camofox Probe ===\n`);
  console.log(`Server: ${CAMOFOX_URL}`);
  console.log(`User: ${USER_ID}`);
  console.log(`Target: ${TEST_URL}\n`);

  // 1. Health check
  try {
    const health = await request('GET', '/');
    console.log(`[health] ${JSON.stringify(health)}`);
  } catch (e) {
    console.log(`[health] FAILED: ${e.message}`);
    return;
  }

  // 2. Create tab
  try {
    const tab = await request('POST', '/tabs', {
      userId: USER_ID,
      sessionKey: SESSION_KEY,
      url: TEST_URL,
    });
    if (!tab.tabId) {
      console.log(`[create] FAILED: ${JSON.stringify(tab)}`);
      return;
    }
    console.log(`[create] tabId: ${tab.tabId}`);
    const tabId = tab.tabId;

    // 3. Navigate
    await new Promise((r) => setTimeout(r, 3000));
    const nav = await request('POST', `/tabs/${tabId}/navigate`, {
      userId: USER_ID,
      url: TEST_URL,
    });
    console.log(`[navigate] ${nav.url || nav.status || 'ok'}`);

    // 4. Snapshot
    await new Promise((r) => setTimeout(r, 3000));
    const snap = await request('GET', `/tabs/${tabId}/snapshot?userId=${USER_ID}`);
    if (snap.snapshot) {
      console.log(`[snapshot] OK — URL: ${snap.url || 'unknown'}`);
      console.log(`[snapshot] Title: ${snap.snapshot.title || 'N/A'}`);
      console.log(`[snapshot] Elements: ${snap.snapshot.elements?.length || snap.snapshot.children?.length || 'N/A'}`);
    } else {
      console.log(`[snapshot] FAILED: ${JSON.stringify(snap)}`);
    }

    // 5. Cleanup
    await request('DELETE', `/tabs/${tabId}?userId=${USER_ID}`);
    console.log(`[cleanup] tab closed`);
  } catch (e) {
    console.log(`[error] ${e.message}`);
  }

  console.log('\n=== Probe complete ===');
}

probe();
