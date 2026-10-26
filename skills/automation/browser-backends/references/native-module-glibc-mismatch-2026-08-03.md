# Native module blocker: `better-sqlite3` glibc mismatch on Oracle Linux 9 aarch64

## Failure signature

```
/lib64/libm.so.6: version `GLIBC_2.38' not found (required by .../better-sqlite3/prebuilds/linux-arm64.node)
```

## Affected tools

- `@askjo/camofox-browser` installed via npm on aarch64 Oracle Linux 9
- `omniroute` installed via npm on the same host

## Why it happens

The npm package ships a prebuilt `better-sqlite3` binary for `linux-arm64`
that was built against a newer glibc than the host provides.

Confirmed environment:
- Host: Oracle Linux 9 aarch64
- `ldd --version`: glibc 2.34
- Required: glibc 2.38

## What does NOT fix it

- `npm rebuild better-sqlite3`
- `npm rebuild better-sqlite3 --build-from-source`

Both can report success while still leaving the incompatible prebuilt in place.

## Verified workaround

Use a Docker-based deployment instead of the host npm package, provided the
image is compatible with the host architecture.

For OmniRoute:
```bash
sudo docker run -d \
  --name omniroute-router \
  --restart unless-stopped \
  -p 8080:20128 \
  -v /home/opc/omniroute/data:/app/data \
  diegosouzapw/omniroute:latest
```

For Camofox on aarch64:
- No verified arm64 image was found for `ghcr.io/redf0x1/camofox-browser`.
- Do not attempt to run an amd64-only image on aarch64; it will fail with `exec format error`.
- Fallback: Playwright-downloaded Chromium + CDP path documented in `browser-backends` SKILL.md.

## Verification

```bash
curl -s -L -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/dashboard
```

Expected: `200` after Docker-based OmniRoute is healthy.
