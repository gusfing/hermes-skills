# Camofox REST API Client Bug: url.pathname drops query params

## Symptom
All Camofox REST API calls fail with errors like:
- `Snapshot failed: {"error":"userId required"}`
- `Tab closed — no action taken`

## Root cause
The HTTP helper function in automation scripts uses:
```js
const options = {
  hostname: url.hostname,
  port: url.port,
  path: url.pathname,  // ← BUG: strips query string
  ...
};
```

`url.pathname` gives only the path portion (`/tabs/{id}/snapshot`),
dropping the query string (`?userId=...`). Camofox's `/snapshot` and
other endpoints require `userId` as a query parameter, so every request
fails.

## Fix
Change to:
```js
path: url.href,  // ← includes query string
```

`url.href` is the full URL including query params, which is what
`http.request()` expects.

## Affected pattern
Any Node.js script using `new URL(base + path)` then passing
`url.pathname` to `http.request()` options will silently drop query
params. This affects Camofox integration scripts that call endpoints
requiring `userId` as a query parameter.

## Scope
This bug appeared in 3 automation scripts in this session:
- `linkedin_message.js`
- `linkedin_campaign.js`
- `post_linkedin.js`

All three had identical `request()` helper functions with the same bug.
