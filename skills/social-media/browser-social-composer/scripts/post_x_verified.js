const { chromium } = require('/opt/data/node_modules/playwright');
const fs = require('fs');

const COOKIES = [
  { name: 'guest_id', value: 'v1%3A178522364709930229', domain: '.x.com', path: '/' },
  { name: 'guest_id_marketing', value: 'v1%3A178522364709930229', domain: '.x.com', path: '/' },
  { name: 'guest_id_ads', value: 'v1%3A178522364709930229', domain: '.x.com', path: '/' },
  { name: '__cuid', value: '4a50a4bc-b9dc-491c-80b0-c9b2d9c1cc10', domain: 'x.com', path: '/' },
  { name: 'g_state', value: '{"i_l":0,"i_ll":1785223651797,"i_b":"8p7RN0UVREt38XKtrwmP+gbfD6T270Kd+LhukGJ/Q/w","i_e":{"enable_itp_optimization":24},"i_et":1785223651797}', domain: 'x.com', path: '/' },
  { name: 'twid', value: 'u%3D1767452684607778816', domain: '.x.com', path: '/' },
  { name: 'auth_token', value: 'ab763f54a69ed8d6545d679ed7750a40974206de', domain: '.x.com', path: '/' },
  { name: 'ct0', value: 'b8f4c2544b27fc7da0cb009078b6562fd3d7b686e1f82b2459261e79f8712fb1c333912d9452f7b02f2aeef26a3071613801f71fd37e7f15bdee66ca6befba01db80c9d430735bbbb7aa09e3fa7cd393', domain: '.x.com', path: '/' },
  { name: 'personalization_id', value: '"v1_HrKgNu+9hmBqXTgOe3SB0g=="', domain: '.x.com', path: '/' },
  { name: 'dnt', value: '1', domain: '.x.com', path: '/' },
  { name: 'lang', value: 'en', domain: 'x.com', path: '/' },
  { name: '__cf_bm', value: 'idNIm2VBZRDRexTxK29KYowxVPVKTmDe0aeDLY1w8ZM-1785435320.2868671-1.0.1.1-YzFh1p7RvErLkgN85y4R7MA0urJa0zQtWBp0dSt_dW4k0loladrYJVyMXUDr2v0QpBU9Hf2dzzLyaeNVHL7OdyQfLuF1CGPsk7rULBbY60WatIiNXcVJKtx8OVrZ0g3G', domain: '.x.com', path: '/' }
];

(async () => {
  const browser = await chromium.launch({
    executablePath: '/opt/data/.playwright/chromium-1234/chrome-linux64/chrome',
    args: ['--no-sandbox','--disable-gpu']
  });
  const context = await browser.newContext();
  await context.addCookies(COOKIES);
  const page = await context.newPage();

  const text = 'hello world test ' + Date.now();
  const out = { text, beforeUrl: '', afterUrl: '', clickResult: '', posted: false };

  await page.goto('https://x.com/compose/post', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);
  out.beforeUrl = page.url();

  await page.focus('[data-testid="tweetTextarea_0"]');
  await page.keyboard.type(text, { delay: 40 });
  await page.waitForTimeout(1500);

  out.clickResult = await page.evaluate(() => {
    const btn = document.querySelector('[data-testid="tweetButton"]') || document.querySelector('[data-testid="tweetButtonInline"]');
    if (!btn) return 'no_button';
    btn.click();
    return 'clicked';
  });

  await page.waitForTimeout(5000);
  out.afterUrl = page.url();

  fs.writeFileSync('/opt/data/outreach/scripts/x-post-last-result.json', JSON.stringify(out, null, 2));
  console.log(JSON.stringify(out));

  await page.screenshot({ path: '/opt/data/outreach/x-post-result.png' });
  await browser.close();
  process.exit(0);
})().catch(e => { console.error('ERR=' + e.message); process.exit(1); });
