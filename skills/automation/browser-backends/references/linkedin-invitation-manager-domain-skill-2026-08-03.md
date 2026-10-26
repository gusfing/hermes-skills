# LinkedIn invitation-manager domain skill

Observed working path for browser-harness on Oracle Linux 9 aarch64.

## Trigger

Use `BH_DOMAIN_SKILLS=1` on host `linkedin.com` when navigating to:
- `https://www.linkedin.com/mynetwork/invitation-manager/received/`
- `https://www.linkedin.com/mynetwork/invitation-manager/received/PEOPLE_WITH_MUTUAL_CONNECTION/`
- `https://www.linkedin.com/mynetwork/invitation-manager/received/PEOPLE_WITH_MUTUAL_SCHOOL/`

Skill file:
`agent-workspace/domain-skills/linkedin/invitation-manager.md`

## Key selectors / behavior

- Accept button: `aria-label` starts with `Accept `, exact form uses curly apostrophe `’` in `Accept <Name>'s invitation`.
- Ignore button: `aria-label` starts with `Ignore `.
- Accept may be `<button>` or `<a>`:
  - `<button>` accepts via JS `.click()` or coordinate click.
  - `<a>` does not accept via CDP click because href points to current page; route those rows to Ignore or skip.
- Pagination: after clicking visible accepts, reload the filter URL. Scroll does not auto-load next batch.
- Safety modal: “Take care when connecting” may appear; click `Accept invite`.
- Loop guard: filter chip count `(N)` decreases per successful accept/ignore; stop when `(0)`.

## Chrome setup used

- Installed `google-chrome-stable` from Google’s aarch64 repo.
- Headless Chrome CDP on `127.0.0.1:9222`.
- `browser-harness` local editable install under `/home/opc/workspace/browser-harness`.
- Attach with explicit `BU_CDP_URL=http://127.0.0.1:9222` if `--doctor` misreports `chrome-not-running`.
- Enable remote debugging in Chrome UI: `chrome://inspect/#remote-debugging` checkbox.

## Demo caveat

If the logged-in GitHub tab is not present in the target Chrome instance, do not ask to star from browser-harness; fall back to `https://browser-use.com`.
