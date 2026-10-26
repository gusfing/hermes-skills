# Dashboard Tunneling Fixes

## localtunnel v2 API

```js
const lt = require('/opt/data/outreach/node_modules/localtunnel');
const tunnel = await lt({ port: 3001 });
const url = typeof tunnel.url === 'function' ? tunnel.url() : tunnel.url;
tunnel.on('close', () => console.log('closed'));
tunnel.on('error', (e) => console.log('error', e.message));
```

Do not call `tunnel.on(...)` before awaiting the promise; in v2 the return value is a Promise that resolves to the tunnel object.

## Serveo SSH reverse tunnel

```bash
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -R 80:localhost:3001 serveo.net
```

- Remote port 3001 often fails with `remote port forwarding failed for listen port 3001`
- Remote port 80 usually succeeds
- Output line: `Forwarding HTTP traffic from https://<subdomain>.serveousercontent.com`

## Validation before presenting URL

```bash
curl -s -o /dev/null -w "%{http_code}" https://<tunnel-url>/
```

- `200` = tunnel healthy
- `502` / `503` / timeout = dead tunnel; do not present to user

## Fallback order

1. localtunnel
2. SSH tunnel: localhost.run, serveo.net
3. If all tunneling fails: use local dashboard + send QR image directly via platform media

## Common failure modes

- Serveo session drops after idle timeout; restart tunnel
- localtunnel subdomain changes between runs; always read URL from tunnel output, never hardcode
- Dashboard QR file missing at boot causes server crash; handler must return 404 for missing `/public/qr.png`
- Stale QR images expire after ~10 minutes; always regenerate before scanning