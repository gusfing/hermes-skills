# VPS SSH Diagnostics — Port Accepts but Doesn't Speak

When SSH to a VPS fails, diagnose which layer is broken before trying fixes.

## Diagnostic sequence

Run these in order — each rules out a different failure class.

### 1. Ping (host alive?)

```
ping -c 1 -W 5 <vps-ip>
```

If ping fails: host is down or ICMP-blocked. Stop here — SSH won't work either.

If ping succeeds: host is reachable. Continue.

### 2. SSH verbose (where does it die?)

```
ssh -vvv -o ConnectTimeout=10 -p <port> user@host
```

Watch the debug output:

| Debug line | Meaning |
|---|---|
| `Connection established.` → then timeout | TCP works, server not speaking SSH |
| `Connection timed out` (during connect) | Firewall blocking, nothing on port |
| `Connection refused` | Nothing listening on that port |
| `No supported authentication methods available` | SSH daemon works, auth config issue |
| `Permission denied` | SSH works, wrong credentials |

### 3. Port-specific pattern

**Port 22 (standard):**
- Often firewalled in hosting environments that use non-standard SSH ports
- `Connection timed out` = firewall, not SSH daemon issue

**Non-standard port (e.g. 2222):**
- If `Connection established` then `timed out during banner exchange`: TCP works but server doesn't respond with SSH banner
- This is DIFFERENT from port 22 timeout — something is listening but not speaking SSH

### 4. Raw TCP read (what does the server send?)

When SSH verbose shows "Connection established" but no banner:

**From Windows PowerShell (when telnet/openssl not available):**

```powershell
$tcp = New-Object System.Net.Sockets.TcpClient
$tcp.Connect("HOST", PORT)
$sr = $tcp.GetStream()
$buffer = New-Object byte[] 256
$startTime = Get-Date
while ($tcp.Connected -and ((Get-Date) - $startTime).TotalSeconds -lt 5) {
    $rv = $sr.Read($buffer, 0, 256)
    if ($rv -gt 0) {
        [System.Text.Encoding]::ASCII.GetString($buffer, 0, $rv)
        break
    }
}
if ($tcp.Connected) { "Still connected after 5s, nothing received" }
$tcp.Close()
```

**From Linux (Python):**

```python
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(8)
s.connect(("HOST", PORT))
s.send(b"SSH-2.0-Client\r\n")
data = b""
try:
    s.settimeout(5)
    data = s.recv(4096)
except socket.timeout:
    pass
s.close()
if data:
    print(f"Server responds: {data[:100]}")
else:
    print("Server silent — something non-SSH is on this port")
```

**Interpreting the result:**
- SSH banner (`SSH-2.0-...`) → SSH daemon works, something kills connection after banner (firewall state issue, rate limit)
- HTTP response (`HTTP/1.1...`, `<!DOCTYPE`) → web server on SSH port (misconfiguration)
- Nothing / silence → wrong service, hung daemon, or firewall that allows connect but drops packets
- Garbage bytes → encrypted protocol on wrong port (TLS, database, etc.)

### 5. Try different users

The user you're connecting as might be disabled or restricted:

```bash
ssh -o ConnectTimeout=10 -p 2222 root@host
ssh -o ConnectTimeout=10 -p 2222 admin@host
ssh -o ConnectTimeout=10 -p 2222 ubuntu@host
```

### 6. Host-side check (if you have console/VNC access)

Through hosting panel web console:

```bash
# What's actually on the SSH port?
ss -tlnp | grep <port>

# Is SSH daemon running?
systemctl status sshd
systemctl status ssh

# VPS firewall
iptables -L -n -v | grep <port>
ufw status
firewall-cmd --list-ports   # firewalld
```

## Common failure patterns

| Symptom | Likely cause | Fix path |
|---|---|---|
| Port 22 timeout, port 2222 established→no banner | Non-standard port configured in hosting panel, but wrong service on that port or hung SSH | Check hosting panel for correct SSH port; inside VPS: `ss -tlnp` to see what's on 2222 |
| Both ports timeout | VPS firewall blocks all SSH, or host-level firewall | Hosting panel firewall rules; cloud security group |
| `Connection refused` on all ports | SSH daemon not installed or not running | Start SSH inside VPS via console |
| Banner exchange timeout, Windows verbose shows established | Something accepts TCP but doesn't speak SSH | Wrong service on port; check `ss` inside VPS |

## Hosting panel access

Most VPS providers offer one of:
- **Web console / VNC** — browser-based terminal, bypasses network issues
- **Serial console** — raw console access, useful when network is broken
- **Recovery / rescue mode** — boot from alternate image to fix the main one

If you can't SSH, use the panel console. It's the only way to diagnose "port accepts but doesn't speak" from the server side.

## What NOT to do

- Don't brute-force password attempts — rate limited, may lock you out
- Don't assume port 2222 is SSH without checking — it could be anything
- Don't retry the same failing command repeatedly — diagnose first
- Don't contact hosting support without checking the panel console first — they'll ask you to do exactly that
