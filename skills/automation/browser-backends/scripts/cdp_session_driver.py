"""Thin raw-CDP driver for the desktop Chrome on :9222.

Measured on this host for LinkedIn and X social scripts. Use when
`connect_over_cdp()` hangs, or when a script needs one deterministic page.

Why raw CDP and not Playwright: measured here, Playwright's `connect_over_cdp`
stalls in the browser-level ws handshake and times out at 45-180s -
reproducibly, while Chrome sits idle at 0.6% CPU with only ~15 targets open,
and again after a clean Chrome restart. The same handshake over a plain
websocket to the SAME webSocketDebuggerUrl returns in ~0.1s.

Consequence: never trust the page you land on. Always goto() the target route
explicitly after attaching, before counting or asserting anything.

Deliberately minimal: evaluate JS, click, type, watch the network. If a selector
stops matching, re-measure it - hashed class names are the usual culprit.
"""
import itertools
import json
import os
import time
import urllib.request

import websocket  # pip install websocket-client

CDP = "http://127.0.0.1:9222"


class Session:
    def __init__(self, url_contains, timeout=30):
        tabs = json.loads(urllib.request.urlopen(
            f"{CDP}/json/list", timeout=15).read())
        pages = [t for t in tabs
                 if t.get("type") == "page" and url_contains in t.get("url", "")]
        if not pages:
            raise RuntimeError(f"no page matching {url_contains!r}")
        self.ws = websocket.create_connection(
            pages[0]["webSocketDebuggerUrl"], timeout=timeout)
        self._ids = itertools.count(1)

    def send(self, method, **params):
        i = next(self._ids)
        self.ws.send(json.dumps({"id": i, "method": method, "params": params}))
        end = time.time() + 40
        while time.time() < end:
            m = json.loads(self.ws.recv())
            if m.get("id") == i:
                if "error" in m:
                    raise RuntimeError(m["error"])
                return m.get("result", {})
        raise TimeoutError(f"{method} no reply in 40s")

    def ev(self, expr, default=None):
        r = self.send("Runtime.evaluate", expression=expr,
                      returnByValue=True, awaitPromise=True)
        res = r.get("result", {})
        if res.get("subtype") == "error":
            raise RuntimeError(res.get("description", "js error"))
        return res.get("value", default)

    def goto(self, url, settle=11.0):
        """Navigate EXPLICITLY. A raw attach lands on whatever tab is open."""
        self.send("Page.navigate", url=url)
        time.sleep(settle)

    def click_xy(self, x, y):
        """Real mouse events. Many sites ignore a JS .click() entirely."""
        for t in ("mousePressed", "mouseReleased"):
            self.send("Input.dispatchMouseEvent", type=t, x=x, y=y,
                      button="left", clickCount=1)

    def click_xy_js(self, expr):
        """Click via JS. Returns whatever the expression returned."""
        return self.ev(expr)

    def focus_and_clear(self, sel_or_expr="[contenteditable=\"true\"]"):
        return self.ev("""(() => {
            const e = %s || document.querySelector('[contenteditable="true"]');
            if (!e) return 'no element';
            e.focus();
            const r = document.createRange(); r.selectNodeContents(e);
            const s = window.getSelection();
            s.removeAllRanges(); s.addRange(r);
            return 'focused';
        })()""" % (sel_or_expr if sel_or_expr.startswith("(") else
                    "document.querySelector(%s)" % json.dumps(sel_or_expr)))

    def type_keys(self, text, delay=0.018):
        """Per-character key events. REQUIRED for tiptap/ProseMirror editors.

        Input.insertText is silently ignored by ProseMirror - the editor stays
        empty. Plain textareas are fine with insert_text().
        """
        for ch in text:
            k = " " if ch == " " else ch
            code = "Space" if ch == " " else ("KeyA" if ch.isalpha() else "Digit0")
            self.send("Input.dispatchKeyEvent", type="keyDown", text=ch,
                      unmodifiedText=ch, key=k, code=code)
            self.send("Input.dispatchKeyEvent", type="keyUp", key=k, code=code)
            time.sleep(delay)
        time.sleep(1.2)

    def insert_text(self, text):
        """One-shot text insert. Fine for textarea / simple contenteditable."""
        self.send("Input.insertText", text=text)
        time.sleep(0.9)

    def key(self, key_name, code=None, windows_vk=None, modifiers=0):
        base = {"key": key_name, "code": code or key_name,
                "windowsVirtualKeyCode": windows_vk,
                "nativeVirtualKeyCode": windows_vk, "modifiers": modifiers}
        self.send("Input.dispatchKeyEvent", type="keyDown", **base)
        self.send("Input.dispatchKeyEvent", type="keyUp", **base)

    def drain_events(self, seconds=0.4):
        """Discard buffered async events so a later read is only about THIS action."""
        try:
            self.ws.settimeout(seconds)
            while True:
                self.ws.recv()
        except Exception:
            pass

    def wait_for_response(self, url_substr, timeout=20):
        """Block until a matching Network.responseReceived arrives; return status.

        THE reliable verification for SPA actions. A DOM read cannot see a
        comment that published; the HTTP status can.
        """
        self.ws.settimeout(1.0)
        end = time.time() + timeout
        while time.time() < end:
            try:
                m = json.loads(self.ws.recv())
            except Exception:
                continue
            if m.get("method") == "Network.responseReceived":
                r = m["params"]["response"]
                if url_substr in r.get("url", ""):
                    return r.get("status")
        return None

    def network_enable(self):
        try:
            self.send("Network.enable")
        except Exception:
            pass

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def cdp_lock(path, name="script", timeout=300):
    """Cross-process lock around the whole browser run.

    Concurrent attaches starve each other: two clients connecting at once both
    stall in the handshake. A killed run leaves this file behind, so store the
    owner pid and let the next run reap an orphan - otherwise the script exits
    with NO OUTPUT at all and looks like a dead browser.

    Use as a context manager: with cdp_lock("/path/.cdp.lock", name="li_engage"):
    """
    import contextlib

    @contextlib.contextmanager
    def _lock():
        me = os.getpid()
        deadline = time.time() + timeout
        while True:
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{name} pid={me} {time.time()}".encode())
                os.close(fd)
                break
            except FileExistsError:
                try:
                    owner = open(path).read().strip()
                    pid = int(owner.split("pid=")[1].split()[0])
                    os.kill(pid, 0)          # still alive?
                except Exception:
                    os.unlink(path)          # orphan, reap it
                    continue
                if time.time() > deadline:
                    raise TimeoutError(f"cdp lock held by {owner}")
                time.sleep(2)
        try:
            yield
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass

    return _lock()


# ---- Verification recipes -------------------------------------------------

# LinkedIn reaction: the label suffix IS the state, so one selector is both the
# control and the check. 'no reaction' -> not liked; anything else -> liked.
LI_REACT_STATE = """(() => {
  const b = document.querySelector('[componentkey] button[aria-label^="Reaction button state"]');
  return b ? b.getAttribute('aria-label') : null;
})()"""

# LinkedIn comment submit: the ONLY trustworthy control. The body text, the
# activity comments tab, the editor clearing, and the "Submitting comment"
# spinner ALL fail to discriminate success from failure.
LI_COMMENT_OK = """(needle) => {
  const ed = document.querySelector('[contenteditable="true"]');
  return {inEditor: ed ? ed.innerText.includes(needle) : false,
          inBody: (document.body.innerText || '').includes(needle),
          editorGone: !ed};
}"""
# ...use: s.network_enable(); s.drain_events(); s.click_xy(x, y)
# ...then:  s.wait_for_response("createComment", timeout=20) == 200

# LinkedIn DM send: Enter does NOT send, it leaves text staged. Click the
# .msg-form__send-button (disabled until the composer has text), then confirm
# the text is in the thread AND the composer cleared.