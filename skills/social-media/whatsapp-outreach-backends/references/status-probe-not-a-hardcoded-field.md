# Probing a chat gateway instead of hardcoding its status

Class of task: a monitoring surface shows a channel as `unreachable` /
`broken` / `not paired` and you need to know which of those is actually true.

## Never let a status field be a guess

The failure this prevents: a dashboard rendered WhatsApp as `unreachable` for a
whole day while the API answered `200` on a listening port. Nobody looked,
because the field looked like a reading.

A status line that is not derived from a live call is a **claim**, not a
measurement — and it silently becomes a false report the moment reality changes.

## Probe the three layers separately, report all three

```
API process      → is the port answering at all?
container/state  → is the backing service healthy?
account/session  → is an account actually usable?
```

These fail independently. Collapsing them into one word destroys the
information the operator needs, because each layer has a different fix.

```python
import json, urllib.request

BASE, KEY, HDR = "http://127.0.0.1:2785", "<key>", "x-api-key"
SID = "<session-id>"

def _get(path, timeout=20):
    req = urllib.request.Request(BASE + path, headers={HDR: KEY})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_error": f"HTTP {e.code}"}
    except Exception as e:
        return {"_error": type(e).__name__}

def status():
    api = "down" if "_error" in _get("/api/health") else "up"
    s = _get(f"/api/sessions/{SID}")
    if "_error" in s:
        return {"api": api, "session": "unknown", "paired": False,
                "note": f"session lookup failed: {s['_error']}"}
    st = s.get("status", "?")
    # paired == a real account, not merely a session row that exists
    paired = bool(s.get("connectedAt")) and st not in ("qr_ready", "disconnected")
    return {"api": api, "session": st, "phone": s.get("phone"),
            "connectedAt": s.get("connectedAt"), "paired": paired,
            "note": "" if paired else "not paired — scan from the phone: "
                                   "WhatsApp > Settings > Linked devices"}
```

`connectedAt` is the field that separates "a session row exists" from "an
account is linked". `status == "qr_ready"` with `connectedAt: null` means the
gateway is fine and nobody has ever scanned the QR.

## Ship the probe, then point the surface at it

Keep the probe as a standalone importable module so both the CLI and the HTTP
route call the same function — that is what stops the two from drifting into
different truths:

```python
import wa_status            # the module above

def render():
    w = wa_status.status()
    print(f"whatsapp  api={w['api']}  session={w['session']}  paired={w['paired']}")
    if w["note"]:
        print(f"  {w['note']}")
```

## Read the credential symbol from the file, never from memory

Probing this gateway needs its key. Guessing the exported name burns a cycle on
an `ImportError` that looks like a broken environment:

```python
# guess:  from secrets import API_MASTER_KEY      -> ImportError
# actual: from secrets import OPENWA_API_KEY
```

Read the module's assignments first (`grep -E "^[A-Z_]+ *=" secrets.py`) rather
than assuming a conventional name. Same class of error as guessing a DB column
or a config key: **look, then use.**

## Verify the three-layer reading is truthful

The whole point is that the new field cannot lie the way the old one did, so
prove it against a live gateway and paste the output:

```
{"api": "up", "session": "qr_ready", "phone": null,
 "connectedAt": null, "paired": false, "note": "not paired — scan from the phone…"}
```

If it prints `unreachable` while `/api/health` returns 200, the probe is still
wrong — re-check which layer it actually read.