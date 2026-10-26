# OCI subnet security list routing diagnosis

## Session: 2026-09-18 — `wa.kawaki.co.in` exposure

## What happened

- SSH to VPS `137.23.36.156` (port 22) worked throughout — confirmed Internet Gateway + routing intact.
- Nginx on port 80 returned 200 from localhost (`curl 127.0.0.1:80`).
- OpenWA container returned 200 on port 2785.
- SELinux `httpd_can_network_connect` was off initially; set to on → internal proxy test passed.
- External `curl 137.23.36.156:80` timed out (000) — no traffic reached the VPS.
- Cloudflare returned 522 — CDN could not reach origin on port 80.
- Firewalld showed port 80 open (http service). iptables input chain was policy ACCEPT with no rules.
- User added security list rule to "Default Security List" — but external port 80 still unreachable.

## Root cause

The security list rule was added to the wrong security list — either:
1. A VCN-level "Default Security List" on a different VCN/subnet, OR
2. The correct subnet's security list but the rule was on an NSG that overrides it.

## How to identify the correct subnet from inside the VPS

_FROM /etc/resolv.conf on the VPS (this session):_
```
search sub08011901030.kunasduias21321.oraclevcn.com
```

Decoded:
- Subnet: `sub08011901030`
- VCN: `kunasduias21321`
- Instance private IP: `10.0.0.22`

## How to navigate OCI Console to the correct security list

```
OCI Console → Networking → VCNs → kunasduias21321
  → Subnets → sub08011901030  (the one with 10.0.0.22)
    → Security Lists → [the list shown here, NOT VCN Default]
      → Ingress Rules → add TCP 80, source 0.0.0.0/0
      → Ingress Rules → add TCP 443, source 0.0.0.0/0 (optional)
```

If the subnet is also attached to a NSG:
```
OCI Console → Instances → [instance] → Network Security Groups
  → [NSG name] → Ingress Rules → same TCP 80/443 rules
```

NSG rules override security list rules — both must allow the traffic.

## What to verify after adding the rule

From a machine OUTSIDE the VPS (not the VPS itself):
```bash
curl -s -o /dev/null -w "%{http_code}" --max-time 15 http://137.23.36.156:80/
# Expected: 200

curl -s -o /dev/null -w "%{http_code}" --max-time 15 http://wa.kawaki.co.in/
# Expected: 200 (via Cloudflare proxy)
```

## Session artifacts

- DNS record created: `wa.kawaki.co.in` → A → `137.23.36.156`, proxied=true (orange cloud)
- nginx config: `/etc/nginx/conf.d/openwa.conf` — proxy_pass to `127.0.0.1:2785`
- Cloudflare API token used: `REDACTED_CLOUDFLARE_TOKEN` (has DNS edit on kawaki.co.in AND pixzaai.com — rotate after use)
- SSH key added to VPS: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINxvvHAsZ5GFUBMUimkAF+EpO0iJtUCBvEGz1IGdyCvj opc@oracle-instance`

## Reproducible diagnosis steps

1. SSH to VPS raw IP (not CDN subdomain)
2. `curl 127.0.0.1:<backend-port>/health` — backend up?
3. `curl 127.0.0.1:80/` — proxy works internally?
4. Check nginx error log: `tail -5 /var/log/nginx/error.log` — 502 + `Permission denied` = SELinux; `Connection refused` = backend down/wrong port
5. `getsebool httpd_can_network_connect` — must be on
6. `ss -tlnp | grep ':80 '` — nginx listening?
7. `sudo firewall-cmd --list-all` — port 80 in services?
8. From outside VPS: `curl <public-ip>:80` — external reachable?
9. If step 8 times out: OCI security list on the correct subnet, or NSG blocking
10. Identify subnet from `/etc/resolv.conf` search domain
11. Navigate to THAT subnet's security list in OCI Console, add ingress rule
12. Re-test step 8 and step 12 (external via CDN domain)
