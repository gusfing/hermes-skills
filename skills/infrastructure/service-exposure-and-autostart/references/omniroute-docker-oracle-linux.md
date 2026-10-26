# OmniRoute on Oracle Linux 9 aarch64

## npm install issue
- `npm install -g omniroute` succeeds, but `omniroute serve` returns 500 because
  `better-sqlite3` ships a prebuilt binary built for glibc 2.38.
- This host has glibc 2.34 on aarch64.
- `npm rebuild better-sqlite3` alone did not replace the prebuilt; running
  `npm rebuild better-sqlite3 --build-from-source` also did not produce a
  usable local source build in this environment.
- Verifying with `node -e "require('better-sqlite3')"` still loaded the
  incompatible prebuilt from `prebuilds/linux-arm64.node`.

## Workaround
- Use the published Docker image instead: `diegosouzapw/omniroute:latest`.
- Existing container observed: `omniroute-router` publishing `0.0.0.0:8080->20128/tcp`.
- Fix for first-run container failure: the bind-mounted data dir `/home/opc/omniroute/data`
  did not exist. Creating it and `chown 1000:1000` resolved the EACCES on
  `/app/data/storage.sqlite`.
- Restarting the container after permissions fixed it resulted in healthy 200/307
  responses; `/dashboard` redirects to `/login`.

## Tailscale exposure
- Tailscale Serve only exposes one root handler per hostname on `:443`.
- If Hermes WebUI already uses `instance-<id>.tail2dfc33.ts.net` for `/`,
  OmniRoute must be reached via its host port, e.g. `http://<tailscale-ip>:8080`,
  or a different Serve hostname if available.
- Do not attempt `tailscale serve --bg --https 8080`; use `--https=8080`.

## Suggested docker run template
```bash
sudo mkdir -p /home/opc/omniroute/data
sudo chown 1000:1000 /home/opc/omniroute/data
sudo docker run -d \
  --name omniroute-router \
  --restart unless-stopped \
  -p 8080:20128 \
  -v /home/opc/omniroute/data:/app/data:rw \
  diegosouzapw/omniroute:latest
```

Verify:
```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/health
curl -s -k -L -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/dashboard
```
