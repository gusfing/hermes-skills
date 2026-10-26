# Medusa v2 Production Deploy to Docker

Specifics for deploying a Medusa v2 (2.17.x) backend as a container stack. Complements
the general process in `SKILL.md`.

## Monorepo Dockerfile

A Medusa v2 backend inside an npm workspace needs the **root** as the build context:

```yaml
build:
  context: .                        # NOT ./apps/backend
  dockerfile: apps/backend/Dockerfile
```

The builder installs from the root lockfile, then builds from inside the app dir:

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
RUN apk add --no-cache python3 make g++ git

COPY package.json package-lock.json turbo.json .npmrc ./
COPY apps/backend/package.json ./apps/backend/
RUN npm ci

COPY apps/backend ./apps/backend
WORKDIR /app/apps/backend
RUN npx medusa build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=9000
RUN apk add --no-cache curl

ENV NODE_PATH=/app/node_modules
COPY --from=builder /app/node_modules /app/node_modules
COPY --from=builder /app/apps/backend/.medusa ./.medusa
COPY --from=builder /app/apps/backend/medusa-config.ts ./
COPY --from=builder /app/apps/backend/package.json ./
COPY --from=builder /app/apps/backend/tsconfig.json ./tsconfig.json
COPY --from=builder /app/apps/backend/src ./src

# deps are hoisted; the app boots from its own workdir
RUN ln -s /app/node_modules /app/node_modules_link \
 && ln -s /app/node_modules_link ./node_modules

EXPOSE 9000
CMD ["sh", "-c", "npx medusa db:migrate && npx medusa start"]
```

Three things that are easy to miss:

- **`tsconfig.json` must be copied into the runner.** The runtime compiles
  `medusa-config.ts` through ts-node; without it you get
  `Couldn't find tsconfig.json. tsconfig-paths will be skipped` followed by
  `Cannot find module '@medusajs/framework/utils'`.
- **Do not COPY `apps/backend/node_modules`.** It does not exist — `npm ci` hoisted
  everything to the root. The build fails with
  `failed to compute cache key: ... "/app/apps/backend/node_modules": not found`.
- **The symlink is not optional.** Without it the app cwd has no `node_modules` and
  resolution fails at boot even though `NODE_PATH` is set.

## Redis Wiring — the Silent-Failure Trap

Medusa v2 reads Redis **only** through module config. A `REDIS_URL` env var alone is
ignored, and the loader falls back to in-memory defaults whose event bus never settles
— so `db:migrate` hangs forever after `Running migrations...`.

```ts
// medusa-config.ts
import { loadEnv, defineConfig } from '@medusajs/framework/utils'
loadEnv(process.env.NODE_ENV || 'development', process.cwd())

// Safe default, NOT an `if`: an env-conditional that yields `{}` violates the
// config type ("Type 'undefined' is not assignable to ..."), and `medusa build`
// runs in an image layer with no REDIS_URL at all.
const redisUrl = process.env.REDIS_URL ?? 'redis://localhost:6379'

module.exports = defineConfig({
  projectConfig: { databaseUrl: process.env.DATABASE_URL, http: { /* cors, secrets */ } },
  modules: {
    // cache and event_bus read a FLAT redisUrl ...
    cache:     { resolve: '@medusajs/cache-redis',     options: { redisUrl } },
    event_bus: { resolve: '@medusajs/event-bus-redis',  options: { redisUrl } },
    // ... but workflow-engine-redis reads a NESTED one. A flat value here makes
    // bootstrap throw "Cannot destructure property 'url' of undefined" and db:migrate
    // hangs with no error printed. This asymmetry is the single most expensive
    // trap in this file — it is NOT a copy-paste-and-adjust block.
    workflows: { resolve: '@medusajs/workflow-engine-redis',
                 options: { redis: { redisUrl } } },
  }
})
```

Confirm the shape against the installed driver rather than trusting the snippet —
each loader destructures its own options, and they do not agree:

```bash
sed -n '1,30p' node_modules/@medusajs/workflow-engine-redis/dist/loaders/redis.js
# const { url, redisUrl, options, redisOptions, ... } = <the options object>
# const resolvedUrl = redisUrl ?? url;
grep -rn "redisUrl" node_modules/@medusajs/{cache,event-bus,workflow-engine}-redis/dist/loaders/
```

`workflow-engine-redis` also needs **`ioredis`** as a direct dependency (it does not
use the `redis` package the other two use). Missing it is a second silent hang.

`Modules.CACHE` (`"cache"`) is the **in-memory** module key; the redis driver is a
separate package and needs an explicit `resolve`. Using the constant alone silently
gets you the wrong module.

### The part that costs you an afternoon

The three redis drivers are **not** in `@medusajs/medusa`'s dependency tree. They may
appear in `node_modules` as orphans pulled in transitively, but:

- `npm ls @medusajs/cache-redis` → `` `-- (empty) ``
- they `require()` cleanly
- they then fail because their peer dependency `redis` was never installed
- Medusa catches that and logs `redisUrl not found. A fake redis instance will be used.`
  — a message that is **false**, since the env var is set correctly

Declare both the drivers and the peer:

```json
"dependencies": {
  "@medusajs/cache-redis": "2.17.2",
  "@medusajs/event-bus-redis": "2.17.2",
  "@medusajs/workflow-engine-redis": "2.17.2",
  "redis": "^4.7.0",
  "ioredis": "^5.4.1"
},
"devDependencies": {
  "ts-node": "^10.9.2"
}
```

### `ts-node` is a runtime requirement, not a dev nicety

The CLI loads `medusa-config.ts` through ts-node. `ts-node` is a **devDependency**, and
`NODE_ENV=production` makes npm omit devDependencies entirely:

```
up to date in 3s                      # npm install, but nothing installed
$ ls -d node_modules/ts-node
ls: cannot access 'node_modules/ts-node': No such file or directory
```

Both `npm install` and `npm install <pkg>` silently no-op, and the lockfile still lists
the package — so "up to date" plus a correct lockfile is **not** evidence it installed.
The symptom is total, not partial:

```
Error in loading config: Cannot find module '/app/.../medusa-config'
Require stack: @medusajs/utils/dist/common/dynamic-import.js
```

Force it, and confirm the directory exists rather than trusting the exit code:

```bash
echo "NODE_ENV=[$NODE_ENV]"; npm config get omit     # -> production, dev
NODE_ENV=development npm install --include=dev --no-audit --no-fund
ls -d node_modules/ts-node
```

`docker compose` does not pass your shell's `NODE_ENV` into the build, so this bites
hardest when you `npm install` on the host to iterate. In an image, the runner needs the
builder's dev deps present on disk — copying `node_modules` wholesale covers it, but a
`--omit=dev` install anywhere will reintroduce this.

## The Isolation Test That Broke the Deadlock

When the same code hangs in a container, **run it outside the container against the same
database** before touching the image again. Publish the deps on loopback only:

```yaml
ports:
  - "127.0.0.1:5432:5432"   # loopback: host app, container DB, not internet-facing
  - "127.0.0.1:6379:6379"
```

```bash
docker run -d --name pg-test -p 127.0.0.1:5432:5432 -e POSTGRES_PASSWORD=... postgres:16-alpine
cd apps/backend && set -a && . ../../.env && set +a && npx medusa db:migrate
```

Outcome is diagnostic:

- **Works on host, still hangs in image** → the app is fine, the image is wrong. Ship it
  on the host under systemd and keep the DB/cache in compose. Do not keep spending
  8-minute builds on a container you already know is defective.
- **Hangs on host too** → the app/config is at fault, and the container was never the
  variable. Keep debugging there.

Either way the ambiguity is gone in one step, which is worth more than the sixth config
edit. See `SKILL.md` Phase 4 for the systemd unit that replaced the container.

Regenerate the lockfile in-container (the host has no install for this workspace):

```bash
docker run --rm -v "$PWD":/w -w /w -u "$(id -u)" node:20-alpine \
  npm install --package-lock-only --no-audit --no-fund
```

Confirm before rebuilding:

```bash
docker compose exec -T <app> sh -c "cd /app && npm ls redis @medusajs/cache-redis"
# both must show a resolved version, not `(empty)`
```

## TypeScript in Dev Scripts

`src/scripts/*.ts` are compiled by `medusa build` and will fail the whole image build.

- `Maybe<T>` is `T | null`. `.filter(c => c?.x != null)` does **not** narrow; use
  `.flatMap(c => c?.x ? [{ x: c.x, flag: c.flag ?? false }] : [])`.
- A payload typed `{ currency_code: string }` rejects `string | undefined`. Coerce with
  `?? fallback` rather than `as`.

## Post-Boot Bootstrap

```bash
docker compose exec medusa npx medusa user -e <email> -p <password>   # admin login
docker compose exec medusa npx medusa exec ./src/scripts/seed-<name>.ts
```

Confirm the seed landed with a row count, not with the exit code:

```bash
docker compose exec -T postgres psql -U <user> -d <db> -tAc "select count(*) from product;"
curl -s http://127.0.0.1:9000/store/products | head -c 400
```

Then set `NEXT_PUBLIC_MEDUSA_BACKEND_URL` to the proxied hostname (not the raw
container IP) and grab a publishable key from the admin UI.

### The seed can log success while writing nothing usable

`"seed complete: 17 products @ ₹600"` and `select count(*) from product` returning 21
are both true while `variants[0].prices` is `null` and `calculated_price` is `{}`. A
missing `region_id` on the request is why: prices resolve per region, so an unscoped
query returns variants with no price attached and the storefront renders blank.

Always check the **region-scoped** payload, which is what the storefront sends:

```bash
curl -s "http://127.0.0.1:9000/store/products?limit=3&region_id=$REGION_ID" \
  -H "x-publishable-api-key: $PK" \
  | python3 -c "import sys,json; p=json.load(sys.stdin)['products'][0]; \
      print(p['variants'][0]['calculated_price']['calculated_amount'])"
```

**Amounts are in minor units.** `where amount = 600` returns 0 rows for a correctly
seeded ₹600 product; the stored value is `60000`. Always confirm the column's unit
before treating an empty result as missing data — check `information_schema.columns`,
then group by value: `select currency_code, amount, count(*) from price group by 1,2`.

### `medusa user` has no publishable-key flag

Creating one needs a script, and `medusa exec` has three shape requirements that each
fail with a distinct error:

| Mistake | Error |
|---|---|
| Top-level `await` in the script | `require() cannot be used on an ESM graph with top-level await` |
| No `export default` | `File doesn't default export a function to execute` |
| `container.resolve('remote_link').save(...)` | `remoteLink.save is not a function` |

The script receives a **container** — follow the shape of your existing seed script,
which is the fastest way to get all four right:

```ts
import { MedusaContainer } from '@medusajs/framework'
import { Modules } from '@medusajs/framework/utils'
import { linkSalesChannelsToApiKeyWorkflow } from '@medusajs/core-flows'

export default async function createPublishableKey({ container }: { container: MedusaContainer }) {
  const salesChannel = container.resolve(Modules.SALES_CHANNEL)
  const [sc] = await salesChannel.listSalesChannels()
  const [pk] = await container.resolve(Modules.API_KEY).createApiKeys([
    { title: 'Storefront', type: 'publishable', created_by: '<admin-email>' },
  ])
  // The key→channel link is a join table, not a column on the channel, so
  // updateSalesChannels({ api_key_id }) throws. Use the same workflow the admin
  // route uses: read the route in
  // node_modules/@medusajs/medusa/dist/api/admin/api-keys/[id]/sales-channels/route.js
  await linkSalesChannelsToApiKeyWorkflow(container).run({ input: { id: pk.id, add: [sc.id] } })
  console.log('PUBLISHABLE_KEY=' + pk.token)
  process.exit(0)
}
```

**Reading the framework's own admin route is the fastest way to learn an API shape.**
Three dead ends here were each solved by reading one route file.

### The public API refuses to serve without a key

`/store/products` returns `{"type":"not_allowed","message":"Publishable API key
required in the request header"}` — a 0-product result is not missing data, it is a
missing header. `/v1/models`-style unauthenticated probing does not apply here.

## Verifying a rotation from the right vantage point

After `ALTER ROLE ... WITH PASSWORD`, the old value must be shown dead **over TCP by
service name**, not from inside the container. `docker compose exec` inherits the
container's own credentials and local-socket auth is usually `trust`, so that test
passes with the old password and proves nothing:

```bash
docker run --rm --network backend_default -e PGPASSWORD=<old> postgres:16-alpine \
  psql -h postgres -U medusa_user -d medusa_bazzaro -tAc 'select 1'
# -> FATAL:  password authentication failed for user "medusa_user"   (rotation real)
```

Two failure modes seen here, both from running `docker compose` in the wrong cwd:

- `no configuration file provided: not found` — compose found no project. The stack
  went down mid-rotation. Recover by re-running from the compose file's directory.
- Running `alter user` through `docker compose exec` while the app held a live pool
  succeeds but does not disconnect existing sessions; restart the app and re-check
  `/health` so a security fix does not become an outage.

Verify data survived the rotation too — table count, row count, and one live API read.

## Storefront CORS

The `STORE_CORS` / `ADMIN_CORS` / `AUTH_CORS` values must list the actual storefront
origin (`https://<storefront-domain>`) **without** a trailing slash. A trailing slash
makes the entry not match and the browser reports a CORS error that looks like a
network failure.
