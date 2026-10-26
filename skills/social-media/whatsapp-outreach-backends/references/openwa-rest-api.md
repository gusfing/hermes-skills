# OpenWA REST API — verified contract (OpenWA 0.23.5, NestJS)

Discovered 2026-09-29 against a real `openwa-api` container. **Routes marked
VERIFIED were executed and returned the stated status. Routes marked BUNDLE
were extracted from the compiled frontend and are not yet exercised — treat
them as a map, not as proof.**

## Auth

- **Header: `x-api-key`.** Not `api_key`, not `Authorization: Bearer`.
- Wrong header name returns **401 even when the value is correct** — an
  easy way to burn an hour. Verify with a 3-way test: no header → 401,
  wrong value → 401, real value → 200.
- Master key source: `docker exec <container> printenv API_MASTER_KEY`.
- Key is 64 hex chars.

## Route-existence probing without docs

NestJS with the SPA shell mounted at `/` makes every unknown path look alive.
Use **status code semantics** instead of guessing:

| Probe | Result | Meaning |
|---|---|---|
| no key on a real route | `401` | route exists, auth required |
| wrong prefix (`/api/v1/...`) | `404` | prefix is wrong |
| `/`, `/api`, `/docs`, `/api-docs`, `/swagger`, `/docs-json` | `200` + HTML | SPA shell, **not** an API doc |

A `200` that returns the SPA shell tells you nothing. Check that the body is
JSON before believing a spec endpoint exists. OpenWA exposes no working
Swagger UI and no JSON spec.

## Verified routes

Base: `http://127.0.0.1:2785`, all under prefix `/api`.

| Method | Path | VERIFIED result |
|---|---|---|
| GET | `/api/sessions` | `200` → `[]` when nothing is paired |
| POST | `/api/sessions` | `201` → session object; see DTO below |
| POST | `/api/sessions/{id}/start` | `200` → status becomes `qr_ready` |
| GET | `/api/sessions/{id}/status` | `200` → `{"statuses":[]}` |
| GET | `/api/sessions/{id}/qr` | `200` → `{"qrCode":"data:image/png;base64,…"}` |

Session object fields: `id`, `name`, `status`, `phone`, `pushName`,
`connectedAt`, `lastActive`, `createdAt`, `updatedAt`, `lastError`,
`restriction`, `engineLoaded`.

Status values seen: `created` → `qr_ready`. `connectedAt` non-null is the
signal a number is actually paired.

`GET /api/sessions/{id}/qr` returns a **base64 data URL, not a file path** —
decode it to a PNG and send the image directly rather than standing up a
dashboard.

## CreateSessionDto — the 400 that isn't about Redis

`POST /api/sessions` returned a bare `{"message":"Bad Request","statusCode":400}`
with **no field detail and nothing in the server log**. The body was valid JSON.
The actual constraint:

```js
@IsString()
@MinLength(3)
@MaxLength(50)
@Matches(/^[a-zA-Z0-9-]+$/, { message: 'Session name can only contain letters, numbers, and hyphens' })
name;
```

**A space in the name fails validation.** `"Kawaki Outreach"` → 400.
`"kawaki-outreach"` → 201. Use `[a-z0-9-]` for every session name you generate.

Optional fields: `config` (only `autoRejectCalls`, `maxReconnectAttempts`,
`reconnectBaseDelay` are read; anything else is stored and ignored),
`proxyUrl` + `proxyType` (`http|https|socks4|socks5`).

Note the DTO's own warning on `proxyUrl`: an unreachable proxy **silently**
blocks the WebSocket — no QR is ever delivered and start times out as
`504`. Leave it unset unless the network genuinely cannot reach WhatsApp.

## Reading the API contract out of the image

When a gateway gives a detail-free 400, the request body is guesswork and the
frontend bundle is minified. **The compiled DTOs are the ground truth.**

```bash
docker cp openwa-api:/app/dist /tmp/owa-dist
ls /tmp/owa-dist/modules/*/dto/*.js
```

NestJS emits `dist/<module>/dto/<name>.dto.js` with the `class-validator`
decorators intact and readable. Also useful:

- `dist/modules/<m>/<m>.controller.js` — every route, method, and guard
- `docker cp openwa-api:/app/dashboard/dist /tmp/owa-dash` then grep
  `assets/*.js` for route strings when no spec is published

DTOs present in this build: `create-session`, `archive-chat`, `chat-summary`,
`delete-chat`, `mark-chat-read`, `mark-chat-unread`, `mute-chat`, plus
`common/auth/dto/is-session-id.validator`.

## Redis-backed features fail open, silently

If a containerized app has no `REDIS_*` env, ioredis defaults to
`localhost:6379` **inside the container**, where nothing listens. Symptoms
that mislead you into chasing the wrong bug:

- Bare `400` on writes, with **no validation detail and no server-log entry**
- Log line `Redis throttler storage failed; failing OPEN (allowing)`
- `ETIMEDOUT` / `ECONNREFUSED` from ioredis on every request

A fail-open rate limiter means the API still *works* — which is why this is
easy to misread as a payload problem. **Check the logs for fail-open warnings
before debugging any unexplained bare 400 on a write route.**

Fix:

```bash
docker run -d --name openwa-redis --restart unless-stopped \
  --network openwa-net redis:7-alpine redis-server --save "" --appendonly no
docker network create openwa-net
docker network connect openwa-net openwa-redis
docker network connect openwa-net openwa-api
```

Two gotchas that cost time:

1. **The default `bridge` network has no DNS.** Connecting by container IP
   works (`PING PONG`) while the hostname does not resolve. Use a
   user-defined network so the service name resolves.
2. **A standalone container has no compose file**, so there is no obvious
   place to set `REDIS_HOST`. Capture the existing env and recreate rather
   than editing a file that isn't there:

```bash
docker inspect openwa-api --format '{{range .Config.Env}}{{println .}}{{end}}' > /tmp/env
# drop PATH/HOSTNAME and any pre-existing REDIS_*, then
docker run -d --name openwa-api --restart unless-stopped \
  --network openwa-net -p 127.0.0.1:2785:2785 \
  -v <preserved volume> \
  -e REDIS_HOST=openwa-redis -e REDIS_PORT=6379 \
  --env-file /tmp/env openwa-openwa:latest
```

**Preserve the volume** (`/app/data` here) or every paired session is lost.

## Running node one-liners inside a container

Inline JS through `sh -c` gets mangled by nested quoting and yields
`SyntaxError` that looks like a missing module. Write the file, copy it in,
and set the working directory so module resolution finds `/app/node_modules`:

```bash
docker cp /tmp/test.js openwa-api:/app/test.js
docker exec -w /app openwa-api node test.js
```

`node /tmp/test.js` fails to resolve `ioredis` even though it is installed —
`require` walks up from the script's directory, and `/tmp` has no
`node_modules` above it. Always land the script inside `/app`.

## Pairing is the human step

`GET /api/sessions` → `[]` means nothing is paired, and **no send route can
work**. Session creation and `qr_ready` are fully automatable; scanning the
QR with a phone is not. Surface the QR image to the user and stop there.
