# browser-harness helpers.py function reference

**Location:** `~/.local/share/uv/tools/browser-harness/lib/python3.12/site-packages/browser_harness/helpers.py` (or `lib64/` on some installs)

**Always read this file first** — it is where the functions live, not SKILL.md.
Import is only available inside a `browser-harness <<'PY' ... PY` CLI session,
not in standalone Python scripts (ModuleNotFoundError otherwise).

## Core functions (538 lines total)

| Function | Signature | Purpose |
|----------|-----------|---------|
| `cdp(method, session_id=None, **params)` | Sends raw CDP command via IPC to daemon | Escape hatch for any CDP method not wrapped by helpers |
| `drain_events()` | Returns `{"events": [...]}` | Drain queued CDP events from daemon |
| `goto_url(url)` | Navigates active tab to URL | Primary navigation helper |
| `page_info()` | Returns `{"url", "title", "w", "h", ...}` | Current page state: URL, title, viewport size |
| `click_at_xy(x, y, button="left", clicks=1)` | Mouse click at viewport coords | Raw coordinate click (use element refs when available) |
| `type_text(text)` | Types into focused element | Simple text input |
| `fill_input(selector, text, clear_first=True, timeout=0.0)` | Fills input by CSS selector | Targeted input fill with optional clear |
| `press_key(key, modifiers=0)` | Presses a key | Enter, Tab, Escape, etc. |
| `scroll(x, y, dy=-300, dx=0)` | Scrolls viewport | Scroll up/down/left/right |
| `capture_screenshot(path=None, full=False, max_dim=None)` | Saves screenshot | PNG screenshot, optional full-page or dimension cap |
| `list_tabs(include_chrome=True)` | Returns list of tab dicts | All tabs including chrome:// pages (filter with include_chrome=False) |
| `current_tab()` | Returns current tab dict | Active tab info |
| `activate_tab(target)` | Activates a tab by targetId | Switches to a specific tab |
| `switch_tab(target, activate=False)` | Switches tab, optional activate | Tab switching with emoji prefix mark |
| `new_tab(url="about:blank")` | Opens new tab | Creates fresh tab |
| `close_tab(target=None)` | Closes a tab | Closes specified or current tab |
| `ensure_real_tab()` | Ensures a non-internal tab exists | Creates one if needed |

## Important patterns

- **Tab management:** When attaching to Chrome with existing tabs, use `list_tabs(include_chrome=False)` to skip internal pages, then `switch_tab(t['targetId'])` to activate the desired tab.
- **Navigation flow:** `new_tab(url)` → `wait_for_load()` → inspect/interact.
- **CDP escape hatch:** Use `cdp()` for any CDP method not wrapped by helpers (e.g. `Runtime.evaluate`, `Network.getAllCookies`).
- **Diagnostics:** `page_info()` returning a dict with `url`, `title`, `w`, `h` confirms the harness is attached and controlling the active tab.

## IPC mechanism

Helpers communicate with the browser-harness daemon via a Unix socket at
`~/.config/browser-harness/runtime/<BU_NAME>.sock` (default name: `default`).
The daemon manages the CDP WebSocket connection to Chrome.
