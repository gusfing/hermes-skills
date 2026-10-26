# Windows PC as Browser Automation Backend (via Tailscale)

## Pattern: Server = Brain, Windows PC = Browser + Storage

Used when:
- Server has no local browser (headless Linux, no GPU, limited RAM)
- User has Windows PC with Chrome installed
- Need persistent browser sessions for social automation (X, LinkedIn, WhatsApp, Instagram)
- Want to offload Chrome memory (1-2GB) from server

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Linux Server (Oracle/Cloud)                                │
│  • Hermes Agent                                              │
│  • 9router (model inference) → port 20128                   │
│  • browser-harness → connects to PC's Chrome CDP            │
│  • Primary storage                                           │
└─────────────────────┬───────────────────────────────────────┘
                      │ Tailscale (secure, works anywhere)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Windows PC (4GB RAM)                                       │
│  • Chrome with CDP on port 9222 (bound to 0.0.0.0)         │
│  • Tailscale connected to same tailnet                      │
│  • Secondary storage / backup                               │
│  • NO Hermes agent needed                                   │
└─────────────────────────────────────────────────────────────┘
```

## Windows PC Setup (PowerShell as Admin)

### 1. Install Tailscale (direct MSI, no winget)
```powershell
$url = "https://pkgs.tailscale.com/stable/tailscale-setup-1.76.3-amd64.msi"
$out = "$env:TEMP\tailscale.msi"
Invoke-WebRequest -Uri $url -OutFile $out
msiexec /i $out /quiet /norestart
$env:PATH += ";C:\Program Files\Tailscale"
& "C:\Program Files\Tailscale\tailscale.exe" up --accept-dns=false
& "C:\Program Files\Tailscale\tailscale.exe" ip -4
```
**Note:** Use full path `C:\Program Files\Tailscale\tailscale.exe` until PATH refreshes.

### 2. Start Chrome with CDP (exposed to Tailscale)
```powershell
$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chromePath)) {
    $chromePath = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
}
$profileDir = "$env:USERPROFILE\chrome-cdp-profile"
if (-not (Test-Path $profileDir)) { New-Item -ItemType Directory -Path $profileDir | Out-Null }

Start-Process -FilePath $chromePath -ArgumentList @(
    "--remote-debugging-port=9222",
    "--remote-debugging-address=0.0.0.0",   # critical: allows external connections
    "--user-data-dir=$profileDir",
    "--no-first-run",
    "--no-default-browser-check"
) -WindowStyle Normal
```

### 3. Firewall Rule (one-time, Admin PowerShell)
```powershell
New-NetFirewallRule -DisplayName 'Chrome CDP Tailscale' -Direction Inbound -LocalPort 9222 -Protocol TCP -Action Allow -Profile Any
```

### 4. Verify
```powershell
Invoke-RestMethod -Uri "http://localhost:9222/json/version"
```
Should return JSON with `webSocketDebuggerUrl`.

### 5. Get Tailscale IP for Server
```powershell
& "C:\Program Files\Tailscale\tailscale.exe" ip -4
```

## Server Configuration

### 1. Update browser-harness .env
```bash
# /home/opc/workspace/browser-harness/.env
BU_CDP_URL=http://<PC_TAILSCALE_IP>:9222
```

### 2. Restart browser-harness
```bash
cd /home/opc/workspace/browser-harness
BU_CDP_URL=http://<PC_TAILSCALE_IP>:9222 .venv/bin/python -m browser_harness.run
```

### 3. Verify Connection
```bash
BU_CDP_URL=http://<PC_TAILSCALE_IP>:9222 .venv/bin/python -c "
from browser_harness import page_info
print(page_info())
"
```

## Key Advantages

- **Isolation**: Each Windows PC can run separate Chrome profiles per account
- **Persistence**: Chrome profile dir survives restarts; login state preserved
- **RAM**: Server stays lean (~1GB vs 2-3GB with local Chrome)
- **Reliability**: Windows Chrome is more stable than Camofox/Playwright on constrained Linux
- **CDP Full Access**: Full DevTools protocol, not limited HTTP session API
- **Tailscale Security**: Encrypted, NAT-traversing, no public exposure

## Multi-Account Pattern

Create separate Chrome profile directories on Windows PC:
```
C:\chrome-cdp-profile-account-a\
C:\chrome-cdp-profile-account-b\
```

Launch separate Chrome instances on different ports:
```powershell
# Account A - port 9222
Start-Process chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chrome-cdp-profile-account-a" ...

# Account B - port 9223
Start-Process chrome.exe --remote-debugging-port=9223 --user-data-dir="C:\chrome-cdp-profile-account-b" ...
```

Server connects to specific account via port:
```bash
BU_CDP_URL=http://<PC_TAILSCALE_IP>:9222  # account A
BU_CDP_URL=http://<PC_TAILSCALE_IP>:9223  # account B
```

## Storage Sync (Optional)

```bash
# On server - sync outputs to PC via Tailscale
rsync -avz /home/opc/carousel-output/ opc@<PC_TAILSCALE_IP>:~/hermes-storage/
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `tailscale` not found after MSI | Use full path `C:\Program Files\Tailscale\tailscale.exe` |
| Chrome CDP not accessible from server | Check Windows firewall rule; verify `0.0.0.0` binding |
| Tailscale IP changes | Tailscale IPs are stable per device; only changes on re-auth |
| Chrome profile lock | `Remove-Item "$profileDir\SingletonLock" -Force` before launch |
| Connection timeout | Verify Tailscale connectivity: `ping <PC_TAILSCALE_IP>` from server |

## When NOT to Use This Pattern

- Need Camofox-specific features (VNC interactive, cookie import API)
- Running on Windows Server with Hermes directly
- No Windows PC available
- Need headless-only (no UI) on server

## Related Skills

- `instagram-carousel-generation` — carousel creation workflow
- `camofox-social-compliance` — Camofox patterns when PC not available
- `camofox-social-fixes` — Camofox troubleshooting