# Reverse-engineering an undocumented container API

You have a containerised service with no docs reachable, an OpenAPI spec that
turns out to be a lie, and a need to call it correctly. Worked example: OpenWA
0.23.5 (NestJS) on port 2785.

**The rule that makes this tractable: the compiled artefact IS the
documentation.** A container image ships the exact version of the code that runs,
so its route table, validators, and defaults are ground truth — not docs you
have to find, and not a version you have to guess at.

## Step 1 — Establish that the docs endpoint is a liar

Many frameworks serve an SPA fallback from `/`, `/docs`, and `/docs-json`, so
those return **HTTP 200 for every path**. A 200 on `/docs-json` is not a spec.

```bash
# If this does not parse as JSON, it is the SPA shell, not a spec.
curl -s http://127.0.0.1:PORT/docs-json | python3 -c "import sys,json; json.load(sys.stdin)"
# -> json.decoder.JSONDecodeError: Expecting value: line 1 column 1
```

Probe a spread of paths and look for a *real* auth failure, not a 404:

```bash
for p in /docs-json /api-docs /swagger /health /api /api/sessions; do
  printf "%-16s %s\n" "$p" "$(curl -s -o /dev/null -m 8 -w '%{http_code}' http://127.0.0.1:PORT$p)"
done
```

A **401 on a plausible business path** is the signal you found the real mount
point. A 404 means wrong path, not wrong auth — do not read it as an auth
result.

## Step 2 — Get the route table out of the image

Never grep inside the container if you can copy out; in-container quoting through
`s docker -c '... sh -c "..."'` mangles regexes and silently returns nothing.

```bash
docker cp <container>:/app/dist /tmp/app-dist
```

**Expect your first regexes to return zero. Zero hits means the regex is wrong,
not that the routes are absent.** This cost several rounds: `@(Get|Post)\\(`,
then `(?:0|common_1)\\.(Get|Post)`, then `\\b(Get|Post)\\(` — all zero across 486
files. The working form, which matches what TypeScript actually emits into
`__decorate([...])`:

```python
pat = re.compile(r"\\(\\s*\\d+\\s*,\\s*[\\w.]*\\b(Get|Post|Patch|Delete|Put)\\s*\\)\\(\\s*['\\\"`]([^'\\\"`]+)['\\\"`]")
```

Enumerate `**/*controller.js` first so you know how many you should find — 31
controllers / 153 routes is a confidence signal that the parse was complete. A
controller file with no extracted routes means the regex missed, not that the
controller is empty.

Group the result by controller file. That grouping is what turns a flat list
into an answer: it is how you tell a real business endpoint
(`GET check/:number` under contact) from a decoy that merely shares a keyword
(`POST validate` under auth = key validation, not input validation).

## Step 3 — Read the DTO when the server returns a bare 400

A 400 with `{"message":"Bad Request","statusCode":400}` and **no field detail**,
plus **no matching entry in the server logs**, means validation rejected the
body before it was logged. The validators are in the DTO:

```bash
# read /tmp/app-dist/modules/<mod>/dto/create-*.dto.js
```

The emitted class-validator decorators are plain and readable:

```js
__decorate([
    (0, class_validator_1.IsString)(),
    (0, class_validator_1.MinLength)(3),
    (0, class_validator_1.Matches)(/^[a-zA-Z0-9-]+$/, { message: '...' }),
], CreateSessionDto.prototype, "name", void 0);
```

This is what actually solved a 400 that two wrong theories had chased: the
`name` field was **rejected because it contained a space** (`/^[a-zA-Z0-9-]+$/`).
The same DTO also documented the unused `config` keys and warned that an
unreachable `proxyUrl` silently swallows the WebSocket with no QR ever delivered.

**Read DTOs for defaults and warnings, not just required fields** — the prose in
`ApiProperty` descriptions often contains the only operational warning in the
product.

## Step 4 — Prove the auth header, do not assume it

A wrong header name returns 401 *even with the correct credential value*, which
looks exactly like a bad key. The dashboard's own bundle names the header:

```bash
docker cp <container>:/app/dashboard/dist /tmp/dash
grep -roE "[A-Za-z-]*[Aa]pi[-_]?[Kk]ey" /tmp/dash/assets/*.js | sort -u
```

Then prove it three ways, which is the only honest verification:

| request | expected | what it rules out |
|---|---|---|
| no key | 401 | endpoint exists, is protected |
| wrong key | 401 | auth is real, not a permissive default |
| real key | 200 + body | the credential works |

Only the third row is evidence the key is good. Rows one and two are controls.

## Step 5 — A dependency the app assumed but never got

OpenWA's ioredis client defaulted to `localhost:6379` *inside* the container,
where nothing listened. Symptom: the app booted healthy while every request
logged `ETIMEDOUT` and, critically, **`Redis throttler storage failed; failing
OPEN (allowing)`** — a rate limiter that silently disables itself under failure
is a security-relevant detail, not a cosmetic log line.

Fix: a dedicated Redis plus a **user-defined network**, because the default
bridge has **no automatic DNS**:

```bash
docker network create app-net
docker network connect app-net <app-container>
docker network connect app-net <redis-container>
# now the hostname resolves; on the default bridge you would have to use the
# container IP, which PONGs but breaks the moment the container restarts
```

Verify with the client's own library, not `nc` — a `PONG` from the app's own
driver is what proves the app's code path works. Two traps hit here: the test
script must live under `/app` (module resolution from `/tmp` cannot see
`/app/node_modules`), and `sh -c` with inline JS mangles quoting badly enough to
produce a syntax error that looks like a connection failure. Write the file,
`docker cp` it in, run it with `docker exec -w /app`.

## Step 6 — Recreating a container that has no compose file

A container started with `docker run` has no compose file to edit, so adding an
env var means recreating it. Capture the full env and the volume mount first —
**dropping the mount silently destroys all session data**:

```bash
docker inspect <c> --format '{{range .Config.Env}}{{println .}}{{end}}' > /tmp/env.txt
docker inspect <c> --format '{{range .Mounts}}{{.Source}}:{{.Destination}}{{end}}'   # volume
docker inspect <c> --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}'
#   ^ empty labels confirm there is no compose file
```

Then re-`docker run` with the original env plus the additions, filtering `PATH`
and `HOSTNAME` which Docker sets itself. Keep this in a script, not as a one-off
command — a container you had to reconstruct by hand will need reconstructing
again, and the env list is the part you will not remember.

## The transferrable lesson

When an API is undocumented, **do not guess, and do not give up on docs** — copy
the compiled artefact out and read the route table, the DTO validators, and the
dashboard's own client code. Order of value: DTO validators > route table >
dashboard bundle > anything the vendor published. A single read of a validator
beat three rounds of guessing at the request body.
