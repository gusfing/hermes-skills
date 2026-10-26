---
name: expose-service-chain-debugging
description: VPS works locally not via internet CDN firewall proxy.
---

# expose-service-chain-debugging

## Trigger

Use when:
- A service running on a VPS returns 200 from localhost/internal but is unreachable from the public internet.
- A CDN (Cloudflare, etc.) returns 522 (origin unreachable) or 502 (bad gateway) and you need to pin the broken layer.
- You're wiring DNS → CDN proxy → VPS firewall → SELinux → reverse proxy → backend and something in the chain is failing.
- SSH access to the VPS is the first troubleshooting step and you need to verify each layer independently.

## Core principle

**Verify each layer independently, in order, before concluding the chain is working.**

A service that returns 200 on `127.0.0.1` is NOT necessarily reachable from the internet. Test the external path explicitly.

## Layer checklist (run in this order)

### 1. SSH access to the VPS

SSH is the entry point for all further checks. If you cannot SSH:
- Verify the SSH key is actually in `~/.ssh/authorized_keys` on the VPS — not just present locally.
- If using a key from a local machine, confirm the public key was appended to the VPS's `authorized_keys`.
- If SSH is via a jump host or different IP, use the raw VPS IP for SSH (not the CDN-proxied subdomain — CDN does not forward SSH).

### 2. Backend health (direct, bypass proxy)

```bash
# Replace 2785 with the actual backend port
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:2785/health
# Or: docker ps | grep <service> ; check container status
```

Expected: 200. If not → backend/container is down or not listening.

### 3. VPS-internal proxy test

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80/
```

Expected: 200 (proxied to backend). If 502 → nginx cannot reach the backend.

### 4. Firewall (firewalld / iptables / ufw)

```bash
# firewalld
sudo firewall-cmd --list-all
# Should show the service/port (e.g. http, https, or the specific port)

# iptables (raw)
sudo iptables -L INPUT -n -v --line-numbers

# what's actually listening
sudo ss -tlnp | grep ':80 '
```

### 5. SELinux (often the silent blocker)

```bash
getsebool httpd_can_network_connect
# Must be 'on' for nginx to connect to backend ports

# If off:
sudo setsebool -P httpd_can_network_connect 1
```

**Pitfall:** nginx returns 502 with `connect() failed (13: Permission denied)` in the error log when SELinux blocks the upstream connection. This is not a firewall issue — it is SELinux.

### 6. Reverse proxy config

```bash
sudo cat /etc/nginx/conf.d/<your-config>.conf
sudo nginx -t
```

Verify `proxy_pass` points to the correct backend address/port and `server_name` matches the expected hostname.

### 7. External port reachability (from OUTSIDE the VPS)

```bash
# From a machine NOT on the VPS:
curl -s -o /dev/null -w "%{http_code}" --max-time 15 http://<VPS-PUBLIC-IP>:80/
```

Expected: 200. If timeout (000) → the port is blocked upstream of the VPS (cloud security list / NSG / provider firewall).

**This is the step most often skipped.** A VPS that passes all internal checks can still be unreachable externally.

### 8. CDN / DNS proxy status

- Confirm the DNS record is proxied (orange cloud ON for Cloudflare).
- Confirm the DNS record points to the correct public IP.
- If CDN returns 522: the CDN cannot reach the origin — go back to layer 7 (external port reachability).
- If CDN returns 502: the CDN reached the origin but the origin returned an error — goes back to layers 3-6.

### 9. Cloud provider security list / NSG (the layer outside the VPS)

**For OCI specifically:**
- The security list rule must be on the **subnet's actual security list**, not the VCN-level "Default Security List".
- Navigate: VCN → Subnets → [the subnet with the instance] → Security Lists → [the list shown there].
- Add ingress rule: TCP 80/443, source `0.0.0.0/0`.
- If the instance is attached to a **Network Security Group (NSG)**, that NSG needs the same rule — NSG rules can override security list rules.

**How to tell which subnet:**
- From the VPS: check the search domain in `/etc/resolv.conf` (e.g. `sub08011901030.kunasduias21321.oraclevcn.com` → subnet `sub08011901030`, VCN `kunasduias21321`).
- From OCI Console: VCN → Subnets → find the subnet matching the instance's private IP.

**How to tell if an NSG is attached:**
- OCI Console → Instances → [instance] → View details → Network Security Groups (if listed, NSG rules apply).

### 10. End-to-end verification (external, via the CDN domain)

```bash
curl -s -o /dev/null -w "%{http_code}" --max-time 15 http://<subdomain>.<domain>/
curl -s -o /dev/null -w "%{http_code}" --max-time 15 https://<subdomain>.<domain>/
```

Expected: 200. Only after this passes is the chain fully verified.

## Common failure patterns

| Symptom | Likely layer | Check |
|---------|--------------|-------|
| SSH works, `curl 127.0.0.1:80` = 200, but `curl <public-ip>:80` times out | Cloud security list / NSG not open for port 80 | Layer 7-9 |
| `curl 127.0.0.1:80` = 502, error log: `connect() failed (13: Permission denied)` | SELinux blocking nginx→backend | Layer 5 (setsebool) |
| `curl 127.0.0.1:80` = 502, error log: connection refused | Backend not listening / wrong proxy_pass port | Layer 2-3 |
| CDN returns 522, VPS external port unreachable | Security list / NSG / provider firewall blocking port | Layer 7-9 |
| SSH to subdomain times out | CDN does not forward SSH; use raw VPS IP | Layer 1 |
| SSH key present locally but rejected on VPS | Key not in VPS `~/.ssh/authorized_keys` | Layer 1 |
| `wa.kawaki.co.in` times out but `137.23.36.156:80` works | DNS points to wrong IP, or CDN proxy not active | Layer 8 |

## Verification script (run on VPS after setup)

```bash
echo "=== nginx ===" && systemctl is-active nginx
echo "=== port 80 ===" && ss -tlnp | grep ':80 '
echo "=== backend container ===" && sudo docker ps | grep <service>
echo "=== backend health ===" && curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:2785/health
echo "=== proxy internal ===" && curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:80/
echo "=== SELinux ===" && getsebool httpd_can_network_connect
echo "=== firewall ===" && sudo firewall-cmd --list-all
```

## OCI-specific notes

- Instance metadata (169.254.169.254) is accessible from within the VPS and can reveal VCN/subnet info via `/opc/v2/vnics/` and `/opc/v2/vcns/` — but requires IMDSv2 token and may be blocked by instance policies.
- `/etc/resolv.conf` search domain usually encodes the subnet and VCN name (e.g. `sub08011901030.vcnname.oraclevcn.com`).
- Internet Gateway must be attached to the VCN and the subnet's route table must have a default route via the IGW — SSH working confirms this is in place.

## Support files

- `references/oci-subnet-security-list.md` — session-specific OCI subnet security list routing diagnosis (this session's `wa.kawaki.co.in` case).
- `references/outbound-restrictions.md` — OCI outbound port blocks and Hostinger SMTP relay workaround via nginx stream proxy (this session's Oracle→Hostinger case).

## Inverse problem: outbound restrictions from cloud VPS

Some cloud providers (OCI, among others) block outbound traffic on certain ports FROM the VPS to external IPs — even when internal connectivity and inbound traffic work fine. This is distinct from inbound firewall issues.

**Symptom pattern:**
- `curl 127.0.0.1:<port>` works internally
- `curl <external-ip>:<port>` from the VPS times out (000)
- SSH to the VPS works (inbound port open)
- The VPS can reach some external ports (e.g. 80 via Cloudflare proxy) but not others

**How to diagnose outbound blocking from inside the VPS:**

```bash
# Test direct IP connectivity (bypasses CDN/DNS)
timeout 5 bash -c "echo > /dev/tcp/<TARGET_IP>/<PORT>" 2>&1 && echo "OPEN" || echo "BLOCKED"

# Test via hostname (may route through CDN)
timeout 5 curl -s -o /dev/null -w "%{http_code}" http://<hostname>:<port>/

# Compare: direct IP vs hostname
# If hostname works but direct IP doesn't → CDN is proxying/allowing the traffic
# If both fail → outbound port is blocked at network level
```

**Cloudflare CDN proxy as bypass:**
When direct IP is blocked but the CDN-proxied hostname works on port 80, the CDN acts as a relay. Services can be reached via the hostname even when the direct IP path is blocked.

**Common blocked outbound ports:**
- Port 25 (SMTP) — blocked by most cloud providers to prevent spam
- Port 587 (submission) — often blocked alongside 25
- Port 2222 (SSH to external) — sometimes blocked
- Port 80 direct IP — occasionally blocked (though HTTP is usually allowed)

**Workaround: TCP stream proxy on the target host**

When the destination host (e.g. Hostinger) is reachable from the internet but the source (Oracle) can only reach it via CDN-proxied port 80, set up nginx stream proxy on the destination:

```nginx
# On the DESTINATION host (not the restricted one)
stream {
    server {
        listen 80;
        proxy_pass 127.0.0.1:25;    # forward to actual service
        proxy_timeout 30s;
        proxy_connect_timeout 5s;
    }
}
```

Then from the restricted host, connect to the destination IP on port 80 — the stream proxy forwards to the real service port. Use IP, not hostname (hostname routes through CDN which may not proxy raw TCP).

**Pitfall — hostname vs IP for stream proxy:**
If you use the CDN-proxied hostname as relayhost, SMTP traffic hits Cloudflare's HTTP proxy which doesn't understand SMTP → connections fail. Use the raw destination IP so traffic goes directly to the nginx stream proxy.

**Pitfall — port 80 already in use:**
If nginx already listens on port 80 for HTTP, adding a stream block on the same port will conflict. Either:
- Use a different port for the stream proxy (if that port is reachable from the restricted host)
- Reconfigure the existing HTTP listener to a different port
- Use socat or a Python TCP relay instead of nginx stream

### Outbound restriction reference

See `references/outbound-restrictions.md` for session-specific details on OCI outbound blocks and the Hostinger SMTP relay workaround.
