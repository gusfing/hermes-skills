# Diagnosing a Service That Hangs With No Error

Worked example. A Medusa v2 container printed `Running migrations...` and then sat
idle forever — no crash, no error, exit 0, container status `Up`. Three config-level
fixes were each plausible and each wrong. The fourth attempt succeeded because it
stopped inferring and measured the process.

The technique generalises to any "hangs after printing `Starting...`" bug.

---

## The Three Wrong Fixes

Each of these *looked* correct against the available evidence. None worked.

| # | Attempt | Why it was plausible | Why it was wrong |
|---|---------|---------------------|------------------|
| 1 | Config reads env var, not explicit module wiring | Log said `redisUrl not found` | Env var was already set correctly and correct |
| 2 | Use `Modules.CACHE` / `Modules.EVENT_BUS` constants | Type names look canonical | Key resolved to the *in-memory* default, not the redis driver |
| 3 | Add `@medusajs/cache-redis` etc. as dependencies | `ls node_modules/` showed them present | They were **orphans**; `npm ls` reported empty; peer dep `redis` still missing |

**Pattern:** all three were config-level edits justified by a log line. All three
rebuilt for ~8 minutes each. The log line was the same in every case.

---

## The Turning Point

`npm ls @medusajs/cache-redis` → `` `-- (empty) ``

The package was on disk but absent from the dependency tree — npm prunes it, so module
resolution can never reach it reliably. Presence on disk and presence in the tree are
different facts. That reframed the problem from "config is wrong" to "a dependency is
missing", which is a checkable claim rather than an edit.

---

## The Decisive Probe

Attach an inspector to the running process and read what it actually holds open.

```bash
# inside the container, single process, no competing CMD
docker compose exec -d <app> sh -c \
  "cd /app && exec node --inspect=0.0.0.0:9229 /app/node_modules/.bin/<entrypoint> > /tmp/m.log 2>&1"

# then evaluate against ws://127.0.0.1:9229
```

```javascript
// what is the process actually holding open?
process.getActiveResourcesInfo()
// -> ["TCPSocketWrap", "Timeout", "Timeout", "Timeout"]

process._getActiveHandles().filter(h => h.constructor.name === 'Socket')
  .map(s => ({ local:  s.localAddress  + ':' + s.localPort,
               remote: s.remoteAddress + ':' + s.remotePort,
               read:   s.bytesRead, written: s.bytesWritten }))
// -> [{ local: "172.20.0.4:49134", remote: "172.20.0.3:5432", ... }]
```

**Result: one socket to Postgres, zero to Redis.**

That single line settles it. The config was correct, the env var was set, the driver
package loaded — and the process had still never opened a Redis connection. No amount
of further config editing could have produced a socket that was never attempted.

Note also `Debugger.paused` callFrames returned only `processTimers`. That is *not* a
dead end: an idle event loop means nothing is executing, which rules out a hot loop
and points at an unsettled promise. It is diagnostic information.

### Reading the same data without a debugger

Hex-encoded `/proc/net/tcp`, state `01` = ESTABLISHED:

```bash
docker compose exec -T <app> sh -c "cat /proc/net/tcp | awk 'NR>1 && \$4==01 {print \$3}'"
# 030014AC:1538  ->  172.20.0.3:5432   (little-endian hex, 1538 = 5432)
# 22051068:01BB  ->  104.16.5.34:443    (an outbound HTTPS call)
```

---

## The Follow-Up That Named the Bug

Socket counts localise the fault; a direct probe names it.

```javascript
// run inside the container
for (const p of ["@medusajs/cache-redis", "@medusajs/event-bus-redis", "redis"]) {
  try { require(p); console.log("OK  " + p); }
  catch (e) { console.log("FAIL " + p + "  " + e.message.split("\n")[0]); }
}
// OK  @medusajs/cache-redis
// OK  @medusajs/event-bus-redis
// FAIL redis  Cannot find module 'redis'
```

The framework's redis drivers `require()` perfectly. They depend on the `redis` npm
package, which was never installed. So the driver loaded, failed to connect, threw, and
the framework caught it and degraded to an in-memory fake — logging a message about a
missing `redisUrl` that had been set correctly the whole time.

**Fix:** add the peer library alongside the drivers, regenerate the lockfile, rebuild.

---

## The Generalisable Lesson

> A dependency that appears in `node_modules` but not in the dependency tree does not
> exist for resolution purposes. Check `npm ls <pkg>`, not `ls node_modules/<pkg>`.

> When a library logs "X not found", verify X is genuinely unused through an
> independent channel before editing config to provide it. Generic degraded-mode
> messages are emitted while the real error is swallowed, and they are frequently
> simply wrong.

> After three plausible-and-wrong fixes, change tool class. Do not write fix four.

## CDP Client Notes

Constraints hit while building a stdlib-only CDP client (no `chrome-remote-interface`
in the container):

- `Runtime.evaluate` runs as **ESM** — `require` is undefined. Read the expression from
  a file with `require('fs')` in the *client*, and for in-page work use
  `Runtime.evaluate` with a plain expression only. Dynamic `import()` fails with
  `ERR_VM_DYNAMIC_IMPORT_CALLBACK_MISSING`.
- `Debugger.pause` on an idle event loop may return only timer frames. Treat that as a
  finding and move to active-handle inspection.
- Attaching to the wrong process wastes a cycle: with a container `CMD` *and* a manual
  `exec` of the same entrypoint, two processes run and `/json/list` shows several
  targets. `pkill -f <entrypoint>` inside the container first, then start exactly one.
- `SIGUSR1` on an already-exited process silently no-ops; check the log actually says
  `Debugger listening` before attaching.
