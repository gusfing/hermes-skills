# SSH Tunnel for Hermes Desktop App — Windows to Oracle Linux Server

## Context

The Hermes desktop app connects to a Hermes gateway running on a remote Linux server. The gateway binds to `127.0.0.1:9120` (loopback only). To connect from a remote Windows machine, an SSH tunnel is required.

## Infrastructure

- **Hermes gateway**: runs on the Oracle Linux server, binds `127.0.0.1:9120`
- **Gateway PID**: check with `cat ~/.hermes/gateway.pid` or `ps aux | grep hermes.*gateway`
- **Public IP**: Oracle Cloud public IP (e.g., `137.23.36.156`) — used for SSH from outside Tailscale
- **Tailscale IP**: `100.93.145.31` — only reachable if the Windows machine is also on the same Tailscale tailnet
- **SSH port**: 22 (must be open in OCI Security Group/Security List AND local firewalld)

## Prerequisites

### Server side (done once)
1. SSH daemon running: `systemctl status sshd`
2. Port 22 open in local firewall: `sudo firewall-cmd --permanent --add-service=ssh && sudo firewall-cmd --reload`
3. Port 22 open in OCI Console Security Group / Security List (ingress rule: TCP 22, source = your Windows IP or 0.0.0.0/0)
4. SSH public key in `~/.ssh/authorized_keys` for the target user (e.g., `opc`)

### Windows side
1. SSH client available: `ssh` in PowerShell or CMD (Windows 10+ has OpenSSH built-in)
2. Private key file (`.key`, `.pem`, or `.ppk` converted to OpenSSH format)
3. PuTTY/Pageant alternative: if using `.ppk` keys, load them into Pageant first

## SSH key permissions on Windows

Windows OpenSSH refuses to use private keys with overly permissive ACLs:

```
Bad permissions. Try removing permissions for user: ...
WARNING: UNPROTECTED PRIVATE KEY FILE!
Permissions for 'C:\Users\...\key' are too open.
```

**Fix with icacls (run in CMD/PowerShell):**
```cmd
icacls "C:\Users\bs209\Downloads\ssh-key-2026-08-02.key" /inheritance:r
icacls "C:\Users\bs209\Downloads\ssh-key-2026-08-02.key" /grant:r "%USERNAME%:(R)"
```

**Fix with PowerShell ACL:**
```powershell
$acl = Get-Acl "C:\Users\bs209\Downloads\ssh-key-2026-08-02.key"
$acl.SetAccessRuleProtection($true, $false)
$owner = New-Object System.Security.Principal.NTAccount($env:USERNAME)
$acl.SetOwner($owner)
$acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) }
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule($env:USERNAME, "Read", "Allow")
$acl.AddAccessRule($rule)
Set-Acl -Path "C:\Users\bs209\Downloads\ssh-key-2026-08-02.key" -AclObject $acl
```

**If using Pageant (PuTTY SSH agent):**
- Load the `.ppk` key into Pageant
- SSH will use Pageant's loaded keys automatically — no `-i` flag needed
- Pageant must be running before SSH connects

## Establishing the tunnel

**PowerShell:**
```powershell
ssh -L 9120:localhost:9120 -i "C:\path\to\private_key" -p 22 opc@137.23.36.156
```

**CMD:**
```cmd
ssh -L 9120:localhost:9120 -i "C:\path\to\private_key" -p 22 opc@137.23.36.156
```

**With Pageant (no -i flag):**
```powershell
ssh -L 9120:localhost:9120 -p 22 opc@137.23.36.156
```

**Tunnel flag breakdown:**
- `-L 9120:localhost:9120` — forward local port 9120 → remote localhost:9120
- `-i` — path to private key file
- `-p 22` — SSH port on remote server
- `opc` — username on remote server
- `137.23.36.156` — remote server's public IP

**Important:** The SSH session will appear idle (no prompt) while the tunnel is active. This is normal. Keep the terminal open — closing it drops the tunnel.

## Verifying the tunnel

From another terminal on the Windows machine:
```powershell
curl http://localhost:9120/
```

Expected: Hermes gateway HTML response (not a connection error). If you get a connection refused or timeout, the tunnel is not working.

Alternative test:
```powershell
curl -s http://localhost:9120/ | Select-String "Hermes"
```

## Connecting the Hermes desktop app

Once the tunnel is active, the desktop app connects to **localhost:9120** on the Windows machine. The SSH tunnel forwards this to the server's Hermes gateway.

**App configuration:**
- **Host**: `localhost` or `127.0.0.1`
- **Port**: `9120`
- Do NOT use the server's public IP or Tailscale IP in the app — the tunnel handles the forwarding

**If the app has separate SSH/tunnel settings:**
- Some apps have a dedicated "SSH tunnel" or "port forward" field
- In that case: set the tunnel field to `9120:localhost:9120` and the app's main host to `localhost:9120`
- Do NOT paste `-L 9120:localhost:9120 opc` into a username field — that's an SSH command flag, not a username

**Common configuration error (observed):**
The desktop app may interpret `-L 9120:localhost:9120 opc` as the SSH username. This fails with:
```
Unsafe SSH target: user must not start with a dash ("-L 9120:localhost:9120 opc").
```
**Fix:** Separate the SSH command into:
- Host: `137.23.36.156`
- Username: `opc`
- Port: `22`
- Port forward/tunnel: `9120:localhost:9120` (in the tunnel field, not username)

## Using Tailscale IP instead of public IP

If the Windows machine is on the same Tailscale tailnet, use the Tailscale IP instead:
```powershell
ssh -L 9120:localhost:9120 -i "C:\path\to\key" -p 22 opc@100.93.145.31
```

This avoids the OCI Security Group requirement for port 22 (Tailscale traffic is encrypted and authenticated at the tunnel layer). However, the Windows machine must have Tailscale running and connected to the tailnet.

**Check Tailscale status on server:**
```bash
tailscale status
```

**Check if Windows machine is on tailnet:**
- Tailscale icon in system tray should show "Connected"
- Or run `tailscale status` on Windows

## Troubleshooting

### SSH connection times out
- OCI Security Group / Security List does not allow inbound TCP 22 from your Windows IP
- Fix: add ingress rule in OCI Console → Compute → Instances → VNIC → Security Lists
- Or use Tailscale IP if Windows is on the tailnet

### SSH connection refused
- SSH daemon not running on server: `systemctl status sshd`
- Port 22 not listening: `ss -tlnp | grep :22`
- Local firewall blocking: `firewall-cmd --list-all`

### Permission denied (publickey)
- Private key path wrong or file doesn't exist
- Key permissions too open (Windows) — apply icacls fix above
- Public key not in server's `authorized_keys`
- Wrong key for this server — try other keys

### Tunnel works but app can't connect
- Tunnel terminal was closed (tunnel dropped)
- App configured with wrong host/port (using server IP instead of localhost)
- App's SSH tunnel field has the wrong format

### Gateway not responding on port 9120
- Hermes gateway not running on server: check `ps aux | grep hermes.*gateway`
- Gateway bound to different port: check `ss -tlnp | grep 9120`
- Gateway crashed: restart with `hermes gateway run` or via systemd

## Key commands for server-side verification

```bash
# Check gateway is running
ps aux | grep hermes.*gateway | grep -v grep

# Check port 9120 is listening
ss -tlnp | grep 9120

# Check gateway PID file
cat ~/.hermes/gateway.pid

# Restart gateway if needed
hermes gateway run &

# Check SSH daemon
systemctl status sshd
ss -tlnp | grep :22

# Check firewall
firewall-cmd --list-all
firewall-cmd --query-service=ssh
```

## Recap

1. Server: SSH running, port 22 open (firewalld + OCI), public key in `authorized_keys`
2. Windows: private key file with correct permissions (`icacls` fix if needed)
3. Windows: run `ssh -L 9120:localhost:9120 -i key -p 22 opc@public_ip` — leave open
4. Windows: verify with `curl http://localhost:9120/` — expect Hermes gateway HTML
5. Desktop app: connect to `localhost:9120`
6. Keep SSH tunnel terminal open for the duration of desktop app use
