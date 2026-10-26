# VansRouter 7844-blocked failure mode — session transcript

## Environment
- Host: Oracle Linux 9 aarch64, 10.9GB RAM
- Docker: 29.7.2, root-only socket (opc needs sudo)
- Tailscale: active, tailnet `dfc33`, Funnel enabled on port 443 only
- cloudflared binary present on host: `/usr/local/bin/cloudflared`, `/usr/bin/cloudflared`, `/home/opc/.9remote/bin/cloudflared`
- Outbound port 7844: **BLOCKED** (confirmed via `timeout 5 bash -c 'echo > /dev/tcp/1.1.1.1/7844'`)

## VansRouter container: what worked
- `docker run --network host --restart unless-stopped` with Tailscale socket mounted
- Env: `JWT_SECRET`, `API_KEY_SECRET`, `INITIAL_PASSWORD`, `DATA_DIR=/app/data`, `PORT=20128`, `NODE_ENV=production`
- **Without** `ENABLE_TAILSCALE_TUNNEL=true` — container stable at ~75MB, no restart loop
- With `ENABLE_TAILSCALE_TUNNEL=true`: in-container cloudflared spawns, hits blocked 7844, gets SIGKILLed, container exits 137 (OOMKilled=false), restart loop

## CLI token computation
Container has no `curl`/`wget`; use host curl or `docker exec ... node -e`.

```bash
# From host (curl available):
machine_id=$(sudo docker exec vansrouter cat /app/data/machine-id)
cli_secret=$(sudo docker exec vansrouter cat /app/data/auth/cli-secret)
cli_token=$(echo -n "${machine_id}9r-cli-auth${cli_secret}" | sha256sum | cut -c1-16)
curl -s -X POST -H "X-9r-CLI-Token: ${cli_token}" -H "Content-Length: 0" http://127.0.0.1:20128/api/tunnel/enable

# From inside container (no curl, use node):
sudo docker exec vansrouter node -e '
const fs=require("fs"),crypto=require("crypto"),http=require("http");
const m=fs.readFileSync("/app/data/machine-id","utf8").trim();
const s=fs.readFileSync("/app/data/auth/cli-secret","utf8").trim();
const t=crypto.createHash("sha256").update(m+"9r-cli-auth"+s).digest("hex").slice(0,16);
const o={hostname:"127.0.0.1",port:20128,path:"/api/tunnel/enable",method:"POST",headers:{"X-9r-CLI-Token":t,"Content-Length":"0"}};
http.request(o,(r)=>{let d="";r.on("data",c=>d+=c);r.on("end",()=>console.log(d));}).end();
'
```

Note: when the container has `ENABLE_TAILSCALE_TUNNEL=true`, calling the tunnel API
inside the container via `docker exec` often fails with "container is restarting"
— race with the crash loop. Compute the token from host-side file reads instead.

## Host-side Cloudflare tunnel (bypass the container's broken cloudflared)

```bash
mkdir -p /tmp/vans-tunnel
cat > /tmp/vans-tunnel/config.yml << 'EOF'
tunnel: vansrouter-20128
credentials-file: /tmp/vans-tunnel/creds.json
protocol: http2
ingress:
  - service: http://localhost:20128
EOF

/usr/local/bin/cloudflared tunnel --url http://localhost:20128 \
  --config /tmp/vans-tunnel/config.yml \
  --no-autoupdate --protocol http2 &

# After ~15s:
cat /tmp/vans-tunnel/creds.json      # tunnel URL lives here
uptime && ps aux | grep cloudflared  # confirm still running
```

**This host: 7844 blocked → host cloudflared ALSO cannot get a URL.**
`creds.json` was never created. The quick tunnel fails at the host level too.
Fallback: Tailscale Funnel (`tailscale funnel on http://localhost:20128`).

## Tailscale Funnel status on this host (pre-VansRouter)

```json
{
  "TCP": { "443": { "HTTPS": true } },
  "Web": {
    "instance-20260802-0122.tail2dfc33.ts.net:443": {
      "Handlers": { "/": { "Proxy": "http://localhost:8080" } }
    }
  }
}
```

Only port 443 is funneled, proxying to localhost:8080. Port 20128 was not funneled.
