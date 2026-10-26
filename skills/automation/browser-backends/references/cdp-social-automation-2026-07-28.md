# CDP Social Automation (2026-07-28)

Observed working path: local Chrome at `127.0.0.1:9222` plus per-account isolated `--user-data-dir` instances.

## Launcher pattern

```bash
DEBUG_DIR_ACCOUNT=/opt/data/chrome-profiles/x_account_a
/opt/data/.agent-browser/browsers/chrome-151.0.7922.47/chrome \
  --headless=new \
  --remote-debugging-port=9222 \
  --user-data-dir="$DEBUG_DIR_ACCOUNT" \
  --no-first-run --no-default-browser-check \
  --disable-gpu --no-sandbox --remote-allow-origins=*
```

Use a different profile dir for each account. Keep the port stable per instance.

## Account identifiers

- `x_account_a`
- `x_account_b`
- `linkedin_account_a`
- `chatgpt_account_a`

## Verification

```bash
curl -I -s http://127.0.0.1:9222/json/version
curl -s http://127.0.0.1:9222/json/list
```

Use `/json/new?https://x.com/compose/post` to open a fresh tab if needed.

## Media upload rule

Do not click visible upload buttons from the accessibility layer. Use the
current browser automation stack’s direct file-input assignment or
equivalent stable upload path.

## Stop conditions

- URL reverts unexpectedly after composer interaction
- Post button stays disabled after all composer inputs are filled
- Upload flow redirects away from composer
- No success indicator within 2 upload/composer state changes
