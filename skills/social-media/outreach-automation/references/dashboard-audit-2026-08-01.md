# Dashboard Audit Findings

Source: delegated audit, 2026-08-01.

## Critical bugs
- `dashboard/server.js:82` forks `/tmp/wa_start.js` but never writes that file; first launch crashes with `ENOENT`
- `dashboard/server.js:64` writes QR to `public/qr.png` without ensuring directory exists
- `dashboard/server.js:124` reports `connected` when launch script forked, not when WhatsApp is actually logged in
- `dashboard/index.html:40` contains SCSS-only `@extend .cta;` in plain CSS, so `.actions button` gets no styling
- `dashboard/server.js:51-55` hardcodes Playwright/Chromium paths without fallback if profile loading fails

## Fixes applied
- Guarded `fs.existsSync(QR_PATH)` before `fs.statSync()` in `/api/wa/status`
- Added empty-body 404 for `/public/qr.png` when QR missing
- Moved WhatsApp launch to non-blocking detached fork

## Remaining gaps
- `/tmp/wa_start.js` is still never written before fork
- `public/` directory creation not ensured
- `connected` flag not replaced with real WhatsApp session check
- CSS `@extend` issue not patched
- Hardcoded paths not parameterized
