# Camofox HTTP-only session API notes

This file captures the HTTP-only Camofox API surface discovered on Oracle Linux 9 aarch64 after fixing the `better-sqlite3` glibc mismatch. This Camofox build does not expose CDP endpoints.

## Health check

```bash
curl -s http://127.0.0.1:9377/
```

Expected:
```json
{"ok":true,"enabled":true,"running":true,"engine":"camoufox","browserConnected":true,"browserRunning":true}
```

## Start browser

```bash
curl -s -X POST http://127.0.0.1:9377/start
```

Expected:
```json
{"ok":true,"profile":"camoufox"}
```

## Open tab

```bash
curl -s -X POST http://127.0.0.1:9377/tabs/open \
  -H 'Content-Type: application/json' \
  -d '{"userId":"default","url":"https://www.linkedin.com","listItemId":"default"}'
```

Expected:
```json
{
  "ok":true,
  "targetId":"c854d79c-9402-42bd-9402-9219c6aafc69",
  "tabId":"c854d79c-9402-42bd-9402-9219c6aafc69",
  "url":"https://www.linkedin.com/",
  "title":"LinkedIn: Log In or Sign Up"
}
```

## List tabs

```bash
curl -s 'http://127.0.0.1:9377/tabs?userId=default'
```

Note: `/tabs` without query returns `{"running":true,"tabs":[]}` even when tabs exist. Always pass `?userId=...`.

## Snapshot

```bash
curl -s 'http://127.0.0.1:9377/tabs/<tabId>/snapshot?userId=default'
```

Returns accessibility-tree YAML with `url`, `snapshot`, `refsCount`, `truncated`, `totalChars`, `hasMore`, `nextOffset`.

## Actions

```bash
# click
curl -X POST http://127.0.0.1:9377/tabs/<tabId>/click \
  -H 'Content-Type: application/json' \
  -d '{"userId":"default","ref":"e13"}'

# type
curl -X POST http://127.0.0.1:9377/tabs/<tabId>/type \
  -H 'Content-Type: application/json' \
  -d '{"userId":"default","ref":"e14","text":"hello"}'

# scroll
curl -X POST http://127.0.0.1:9377/tabs/<tabId>/scroll \
  -H 'Content-Type: application/json' \
  -d '{"userId":"default","direction":"down"}'

# evaluate JS
curl -X POST http://127.0.0.1:9377/tabs/<tabId>/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"userId":"default","expression":"document.title"}'

# screenshot
curl -s 'http://127.0.0.1:9377/tabs/<tabId>/screenshot?userId=default' --output /tmp/tab.png
```

## Cookies

```bash
curl -X POST http://127.0.0.1:9377/sessions/:userId/cookies \
  -H 'Content-Type: application/json' \
  -d '{"cookies":[{"name":"...","value":"...","domain":".linkedin.com","path":"/","httpOnly":true,"secure":true}]}'
```

Cookie caveat: this Camofox build rejects `expires: null`. For session cookies, omit `expires` entirely. For expiring cookies, pass `expires` as a numeric Unix timestamp.

## Limitations vs CDP

- No `/json/list`, `/json/version`, or WebSocket debugger URLs
- `browser-harness` cannot attach
- Complex multi-tab orchestration is harder; prefer Chrome CDP for that
- Some routes may be plugin-declared but not actually mounted; validate by calling them
