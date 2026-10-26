# Browser-profile isolation when installing third-party automation

Session: 2026-10-02, installing `tweetytweets` alongside an existing logged-in
Chrome on CDP 9222 holding X and LinkedIn sessions.

## The hazard

The new skill's README:

> "Never drive the user's everyday browser profile. Only the dedicated one."

Its code:

```python
def ensure_chrome(wait=25, url="about:blank"):
    if alive():
        return True
    ...
    subprocess.Popen([chrome, f"--remote-debugging-port={_port()}",
                      f"--user-data-dir={prof}", ...])
```

`alive()` is a **port check**, not an identity check. On a machine where
something already holds the debugging port, the guard returns early and the
dedicated-profile branch never runs. The README's promise is exactly the
property the code fails to enforce.

Note the config default is `port: 9222` — the most common CDP port in the world,
and the one this host already used.

## Pre-flight, in order

```bash
# 1. what already holds the port?
ss -tlnp | grep 9222

# 2. read the attach path. does it verify WHICH browser, or only that a port
#    answered?  grep -n -A20 "def ensure_chrome\|def launch" scripts/browser.py

# 3. what does it think its handle is?
timeout 120 python scripts/post.py check
```

## Configuration that isolates it

```json
{
  "browser": {
    "port": 9333,
    "profile_dir": "/home/opc/.tweety-chrome",
    "headless": false
  }
}
```

## Confirming isolation empirically

Do not trust the config. Check the process table:

```bash
pgrep -af "user-data-dir" | grep -oE "user-data-dir=[^ ]*" | sort -u
```

Correct result — the new profile appears **alongside** the old ones:

```
/opt/data/sessions/session-d81af546-...
/home/opc/.li-chrome-profile
/home/opc/.tweety-chrome
```

If the pre-existing profile disappears, you overwrote it. Also confirm both
ports listen side by side (`ss -tlnp | grep -E "9333|9222"`).

## Reading the account check correctly

```
{"error": "not logged in", "logged_in": false, "handle": null}
```

**This is correct behaviour, not a failure.** A driver whose own browser is
empty must refuse to post rather than posting as nobody. An empty account check
here says nothing about the driver's quality — it says the new browser has no
session yet.

## Bonus: pitfalls worth borrowing regardless

From that repo, both already paid for once:

- **The profile timeline renders stale for up to a minute after sending.** A real
  successful post was reported as failed because the read-back ran 6 seconds too
  early and saw a five-month-old post. Poll the read-back.
- **A green "Your post was sent" toast is not proof.** Read the profile back.
- **Vision is unreliable for numbers** — it has misread a post count and invented
  navigation items. Never let a vision reading override the DOM or `state.json`
  for counts. It *is* reliable for post text and line breaks.
- **Don't name a script after a stdlib module** (`inspect.py`, `queue.py`) — the
  scripts directory lands on `sys.path` and the name shadows the real import.
  This host has already been bitten by `/tmp/inspect.py`.

## Stdlib-shadow check

```bash
ls scripts/ | grep -xE "inspect|queue|types|copy|json|hash|random|dataclasses|enum|abc|io|os|time|code" \
  && echo "SHADOW RISK" || echo "clean"
```
