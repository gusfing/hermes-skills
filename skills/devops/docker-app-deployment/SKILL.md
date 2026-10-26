---
name: docker-app-deployment
description: "Deploy Docker/compose app stacks to a VPS and verify them."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [docker, compose, deployment, vps, nginx, dns, medusa, nodejs]
    related_skills: [linux-server-panel, expose-service-chain-debugging]
---

# Docker App Deployment to a VPS

## Overview

Deploying a containerised application stack to a Linux VPS: take a repo's Dockerfile +
docker-compose.yml, get it building, get it running, put it behind a subdomain, and
prove it works with evidence rather than container state.

**The governing principle: a container reporting `Up` proves nothing.** Every claim in
this skill is verified against something externally observable — an HTTP status, a row
in a table, an open socket.

## When to Use

- "Deploy this to my VPS / the server / Cockpit"
- A repo arrived with a Dockerfile + docker-compose.yml (often AI-generated) and a
  step-by-step deploy guide that you should sanity-check before running
- A stack builds but a service hangs, crash-loops, or never becomes reachable
- You need a new service exposed on a subdomain through nginx + Cloudflare

**Not for:** installing a server control panel (see `linux-server-panel`), or
debugging application logic once deployed.

---

## Phase 1 — Review Before Running

Never pipe a supplied deploy config straight into `docker compose up`. These configs
are frequently generated and routinely broken. Read them first.

```bash
# 1. Private repo? You need auth before anything else.
git clone https://github.com/owner/repo.git /home/<user>/<name>   # fails if private
ls ~/.ssh/id_*.pub && ssh -T git@github.com    # SSH route: add pubkey in GitHub UI
gh auth status                                   # or: gh auth login

# 2. Environment sanity
docker --version && docker compose version
df -h / && free -h
ss -tlnp | grep -E ':<appport>|:5432|:6379'    # port collisions before you start
```

Then read every file and check:

- [ ] **Build context vs. Dockerfile COPY paths.** The most common break. In an
      npm/pnpm/yarn workspace, `npm ci` needs the *root* lockfile. A Dockerfile with
      `context: ./apps/backend` cannot see `backend/package-lock.json` and fails
      immediately. Set `context: .` and point `dockerfile:` at the nested path.
- [ ] **Workspace hoisting.** `npm ci` in a workspace hoists deps to the root
      `node_modules`; the app dir often has *no* `node_modules` at all. Anything the
      runtime resolves from its own cwd needs that path visible (Phase 4).
- [ ] **Hardcoded secrets in committed files.** `POSTGRES_PASSWORD: my_secure_password_2026`,
      hardcoded `JWT_SECRET`/`COOKIE_SECRET`. Regenerate at deploy time, keep real
      values in a gitignored `.env`. If the repo was already committed with live
      secrets, moving them to `.env` is **not** enough — they stay in git history and
      must be rotated, then verified dead (see Phase 6).
- [ ] **Databases published to the internet.** `ports: ["5432:5432"]` on a DB/cache
      service is public exposure. Delete the `ports:` block — services on the same
      compose network reach each other by service name without it.
- [ ] **Pinned base images and healthchecks.** `image: postgres:16-alpine`, plus
      `healthcheck:` + `depends_on: condition: service_healthy` so the app waits for a
      genuinely ready DB, not a started one.

---

## Phase 2 — Build Failures

### DNS failures inside the build

```
WARNING: fetching https://dl-cdn.alpinelinux.org/...: DNS: transient error
ERROR: unable to select packages: curl (no such package)
```

This is *not* "no internet". The host resolves fine interactively; the cloud provider's
internal resolver (OCI uses `169.254.169.254`) rate-limits the parallel queries a
buildkit build fires off. Pin public resolvers for the daemon:

```bash
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
  "dns": ["1.1.1.1", "8.8.8.8", "9.9.9.9"],
  "dns-opts": ["timeout:5", "attempts:3"]
}
EOF
sudo systemctl restart docker
```

### TypeScript errors in a runtime-image build

A dev helper script (e.g. `src/scripts/add-inr.ts`) can fail `medusa build` and take the
whole deploy with it. Two recurring shapes:

- `Maybe<T>` is `T | null`. `arr.filter(c => c?.x != null)` does **not** narrow the
  element type — use `flatMap` to produce a definite shape.
- An update payload typed `string` won't accept `string | undefined` even if the value
  is always present at runtime. Coerce with `?? fallback` rather than `as`.

Fix the types properly. Do **not** disable `tsc`, add `--skipLibCheck` to mask real
errors, or delete the script to get a green build — that is deleting someone's tooling
to hide a defect.

### Cache-miss COPY

```
failed to compute cache key: failed to calculate checksum of ref ...:
  "/app/apps/backend/node_modules": not found
```

The source path does not exist in the builder stage. Almost always the hoisting case —
the app dir has no local `node_modules`. Remove the COPY.

---

## Phase 3 — The Hang

A service that prints `Running migrations...` and then sits there forever is the most
common deploy failure and the most commonly misdiagnosed. **A log line claiming a
dependency is missing is a hypothesis, not a finding** — libraries print generic
degraded-mode messages while swallowing the real error.

Escalate from inference to measurement, in this order:

1. **Read the process's actual state, not its config.** Attach an inspector and read
   live state — full procedure in `references/hanging-service-diagnosis.md`. The
   highest-value probe is a *socket count per dependency*: a config that looks entirely
   correct (env var set, module wired, driver `require()`s cleanly) while the process
   holds **zero** sockets to that dependency proves the code never tried to connect.
   Compare against a dependency that *does* work — "one socket to Postgres, none to
   Redis" localises the fault immediately, as a fact rather than an inference.
2. **Probe the dependency directly** in isolation. Often what finally names the bug: a
   driver package that `require()`s fine while its own peer dependency is absent.
3. **Verify presence, not just on-disk existence.** `ls node_modules/<pkg>` proves
   nothing if the package is an orphan rather than a declared dependency — `npm ls <pkg>`
   returning `` `-- (empty) `` means npm will prune it. A directory can exist while
   being invisible to module resolution.

### The classic cause: transitive peer dependencies

A framework's optional integration packages (`@medusajs/cache-redis`,
`@medusajs/event-bus-redis`, `@medusajs/workflow-engine-redis`) can sit in
`node_modules` as *orphans* pulled in transitively, yet be absent from the dependency
tree. They `require()` cleanly, then fail to open a connection because the peer library
they need (`redis`) was never installed. The framework catches the failure and silently
degrades to an in-memory fake — which is exactly why a correct-looking config produces
a hang with a misleading log line.

**Fix:** declare the integration packages *and* their peer library explicitly, then
regenerate the lockfile:

```bash
# in the app's package.json add e.g. "redis": "^4.7.0" alongside the drivers
docker run --rm -v "$PWD":/w -w /w -u "$(id -u)" node:20-alpine \
  npm install --package-lock-only --no-audit --no-fund
```

**ponytail:** there is no durable lockfile-level fix for this class — it recurs whenever
a framework adds an integration whose peer dep is undeclared upstream. Re-check
`npm ls` after every dependency bump.

### Stop rule

After three fixes have each been plausible and each wrong, **do not attempt a fourth
config edit.** Switch tool class (inspector, direct probe, asserted fact) or report
that the diagnosis is incomplete. A fourth 8-minute build that also fails is worse than
saying "here is the state that contradicts my hypothesis, I don't know yet."

**The stop rule has an escape hatch: change the variable, not the config.** When the
next move is another config edit and the evidence is "everything I can see is correct,"
stop editing and change *where the code runs*. Run the app on the host against the same
database (deps published on `127.0.0.1` only) — one run decides whether the app or the
image is at fault, and either answer ends the guessing. Details and the systemd unit
that replaced the container: `references/medusa-v2-production-deploy.md`.

Mixing runtimes is a legitimate outcome, not a failure. A Node app on the host under
systemd + Postgres/Redis in compose on loopback is a normal production shape. Say
plainly what still does not work in the container rather than implying the image was
fixed.

### Report the wall honestly

When a phase ends unresolved, say what works, what blocks, and which options remain —
and do not dress a dead end up as a working method. The user's trust in every other
claim depends on the blocked one being accurately described.

---

## Phase 4 — Runtime Resolution

Multi-stage builds frequently break module resolution in the runner stage. Symptom:
`Cannot find module '@scope/pkg'`, or a config that "cannot find module .../utils" even
though the file is present in the image.

```dockerfile
# deps hoisted to /app/node_modules by the workspace install; the app boots from
# its own workdir, so expose them locally as well as on NODE_PATH.
ENV NODE_PATH=/app/node_modules
RUN ln -s /app/node_modules /app/node_modules_link \
 && ln -s /app/node_modules_link ./node_modules
```

Also copy the config files the runtime compiles, not just source and build output:
`tsconfig.json`, `package.json`, `medusa-config.ts`, `.medusa/`. Without `tsconfig.json`
a ts-node-based runtime prints `Couldn't find tsconfig.json` and resolves nothing.

**Conditional config, correctly:** an env-dependent `if` yielding `{}` can still violate
a config type (an empty object fails an index signature). Read the env var with a safe
default so the config shape is identical in every environment:

```ts
const redisUrl = process.env.REDIS_URL ?? 'redis://localhost:6379'  // shape always valid
```

---

## Phase 5 — Expose It

**nginx** — prefer a proxy over publishing the app port directly:

```nginx
server {
    listen 80;
    server_name api.example.com;
    client_max_body_size 50M;
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;      # websockets
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Don't duplicate a `proxy_set_header` across an include — nginx errors on a repeated
directive at the same level.

**Cloudflare** — create the A record, proxied:

```bash
curl -s -X POST -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  -d '{"type":"A","name":"api","content":"<vps-ip>","ttl":1,"proxied":true}' \
  "https://api.cloudflare.com/client/v4/zones/$ZONE/dns_records"
```

- `ttl: 1` = automatic. `proxied: true` = orange cloud.
- **Cloudflare proxies HTTP/HTTPS only.** Pointing a *mail* or raw-TCP protocol at a
  proxied record does not work. An IPv6 client will try the proxied AAAA and fail with
  `Network is unreachable` — bracket the target to force IPv4, or use a grey-cloud
  record for non-HTTP traffic.
- A token failing `/user/tokens/verify` may still have working DNS scope. Test the
  endpoint you actually need before concluding the token is dead.

**Verify DNS:** `dig +short api.example.com` returning Cloudflare anycast IPs rather than
your origin is *correct* for a proxied record.

---

## Phase 6 — Verify With Evidence

Container state is not verification. All of these must pass:

```bash
# 1. HTTP actually answers
curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 http://127.0.0.1:9000/health
curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 http://api.example.com/health

# 2. Migrations/seed really applied — count rows, don't read "Up"
docker compose exec -T postgres psql -U <user> -d <db> -tAc \
  "select count(*) from information_schema.tables where table_schema='public';"
docker compose exec -T postgres psql -U <user> -d <db> -tAc "select count(*) from <table>;"

# 3. The app returns real data through the API, not just 200
curl -s http://127.0.0.1:9000/store/products | head -c 400

# 4. The dependency is genuinely in use
docker compose exec -T <app> sh -c "cat /proc/net/tcp | awk 'NR>1 && \$4==01 {print \$3}'"
```

Then complete the app-specific bootstrap — admin user, seed data, publishable API key —
before pointing a frontend at it. A storefront wired to a backend with no products and
no publishable key fails at first render, which looks like a frontend bug and is not.

**Verify a secret rotation actually took.** Moving a credential out of a committed file
is not rotation. After changing it in the store, prove the old value is dead:

```bash
# from a separate container on the same compose network, hitting the service BY NAME so
# the TCP path is exercised
docker run --rm --network <net> -e PGPASSWORD=<old> postgres:16-alpine \
  psql -h postgres -U <user> -d <db> -tAc 'select 1'
# -> FATAL:  password authentication failed for user "..."   (rotation worked)
```

Two traps here:

- `docker compose exec` **inherits the container's own already-correct credentials**, and
  local-socket auth is often `trust` — so a test run that way passes even with the old
  password and proves nothing. Use a throwaway container with explicit `-e PGPASSWORD`.
- Rotating the DB password means restarting the app too. Confirm `/health` still returns
  200 afterwards, or you have traded a security fix for an outage.

**Report state honestly.** "Container is Up" is not "deployed". If verification did not
run, say so.

---

## Pitfalls

- **`docker` permission denied for a non-root user.**
  `permission denied while trying to connect to the docker API at
  unix:///var/run/docker.sock`. The user isn't in the `docker` group.
  `sudo usermod -aG docker <user>` — but group changes need a *new login session*.
  In an existing session `sg docker -c '<cmd>'` picks it up immediately, which matters
  for background/automated runs.
- **Two processes running the same one-shot command.** If a container `CMD` runs
  `migrate && start` and you also `exec` a manual migrate, both run concurrently and
  fight over the same rows/locks. When debugging a hang, `pkill -f <cmd>` inside the
  container first and run exactly one.
- **`docker compose down` keeps named volumes**, so a database persists across a full
  down/up. Use `down -v` to actually reset.
- **`docker compose up -d` exit 0 does not mean the service booted.** A crash-loop
  container reports success at start and dies seconds later. Sleep, then re-check logs.
- **A long build exceeds the foreground tool timeout.** Multi-stage Node images run
  8+ minutes; a 900 s request is rejected outright. Use `background=true, notify=true`
  and do other work while it runs. Do not sit in a poll loop.
- **An interactive TTY blocks a foreground call.** A command that opens a browser, a
  prompt, or a pager will hang the tool even when the underlying work is fine. Add
  `--no-browser` / `--yes` / `-T` equivalents, or run it detached with `exec -d`.
- **A 404 or a CSP warning in the browser console is usually not a deployment fault.**
  An admin SPA shipping `default-src 'none'` will block third-party analytics by
  design, and a missing `/favicon.ico` is cosmetic. Check what the page actually
  loaded and what the real endpoints return before investigating.
- **The guide's port numbers are often wrong.** Supplied instructions may point an admin
  UI at the control-panel port instead of the app port. Trust the compose file.
- **Cloning a private repo needs auth before anything else works** — otherwise every
  later step fails on a confusing error.
- **Multiple unrelated services on one small VPS.** Check `free -h` and `df -h` before
  adding a stack; a 10 GB host already running mail and panels is tight.
- **The default bridge network has no automatic DNS.** `docker run` without
  `--network` puts a container on `bridge`, where a service name does *not*
  resolve — even to another container. `getent hosts <name>` returns nothing
  while a direct connect to the container IP works fine, which is the confusing
  signature. Create a user-defined network and `docker network connect` both
  containers to it. The IP works, but it changes on every restart; the hostname
  is what you actually want in the app's config.
- **A container with no compose file cannot be reconfigured, only recreated.**
  Check for one with
  `docker inspect <c> --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}'`
  (empty = started by hand). To add an env var, capture the full env *and the
  volume mount* with `docker inspect` first — re-running without the `-v` mount
  silently discards all the container's data, which for a stateful service looks
  like an unexplained total loss.
- **A dependency the app silently fails open on is worse than a crash.** Watch
  logs for degraded-mode phrases — `failing OPEN`, `falling back to in-memory`,
  `ETIMEDOUT` — during a healthy-looking boot. An app that stays `Up` while its
  rate limiter has quietly disabled itself is not verified.

## References

- `references/hanging-service-diagnosis.md` — worked example: three wrong config-level
  fixes, then the inspector/socket-count probe that found the real cause
- `references/medusa-v2-production-deploy.md` — Medusa v2 specifics: workspace
  Dockerfile, redis module wiring, seeding, admin user
- `references/reverse-engineering-container-apis.md` — driving a service with no
  reachable docs: telling a fake `/docs` SPA from a real spec, extracting the
  route table from compiled output, reading DTO validators to solve bare 400s,
  proving an auth header three ways, and recreating a compose-less container
  without losing its volume
