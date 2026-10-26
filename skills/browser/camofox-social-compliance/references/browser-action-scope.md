# Browser Action Scope for Social Automation

## Available actions

These are the browser actions available in the Camofox/Social automation stack:
- `browser_navigate` / `navigate` - open URLs, maintain tab state
- `browser_snapshot` / `snapshot` - get accessibility tree and element refs
- `browser_click` / `click` - interact with elements by ref ID
- `browser_type` / `type` - enter text into input fields by ref
- `browser_press` / `press` - keyboard actions like Enter, Escape
- `browser_scroll` / `scroll` - scroll page content
- `browser_console` / `console` - read browser errors
- `browser_get_images` / `images` - enumerate page images
- `browser_vision` - screenshots for visual QA/state checks
- `browser_forward` / `browser_back` - history navigation
- `evaluate` - execute JS in the page context
- `screenshot` - capture PNG screenshot of current tab
- `/tabs` and `/tabs/{tabId}/*` - create, manage, and interact with browser tabs
- `/sessions/{userId}/cookies` - import/export cookies
- `/sessions/{userId}/storage_state` - export full Playwright storage state

## Social task mapping

| Task | Preferred action | Fallback |
|---|---|---|
| Open composer on X | `evaluate` JS opener | `/tabs` navigate then snapshot |
| Type post text | `browser_type` by ref | `evaluate` DOM write |
| Submit post | `browser_press Enter` | `browser_click` Post ref |
| Media upload | manual-complete handoff | file input ref click if available |
| Verify post success | snapshot/screenshot scan | URL/status checks |
| Cookie import | `/sessions/{userId}/cookies` Netscape format | manual export |
| Session persistence | `userId`+`sessionKey` reuse | `storage_state` export |
| Emergency login | VNC interactive if available | fresh cookie import |

## Constraints

- No browser tools support uploading files from the Hermes filesystem directly via accessibility refs
- Camera/mic/webcam access is unavailable in headless/Camofox contexts
- Robotic/automation fingerprints may trigger anti-bot challenges on social platforms
- CAPTCHAs and MFA require VNC/manual intervention or fresh cookies from a clean session
- X media upload via browser refs is unreliable; prefer manual handoff or real X API upload when possible
