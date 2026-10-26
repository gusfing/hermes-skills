# Oracle VPS Access Patterns

## Hermes Dashboard Access After Fresh Install

- `hermes dashboard` binds to `127.0.0.1` and validates the `Host` header
- Tailscale serve changes the `Host` header, causing `{"detail":"Invalid Host header"}`
- Public-bind `--host 0.0.0.0` requires auth provider; `--insecure` is deprecated/no-op as of June 2026

Working access methods:

1. SSH port forwarding (recommended)
   ```powershell
   Start-Process ssh -ArgumentList "-N","-L","9120:127.0.0.1:9120","-i","keypath","user@host" -WindowStyle Hidden
   ```
   Then open http://localhost:9120

2. Hermes CLI directly via SSH
   ```bash
   ssh -i key user@host
   hermes chat
   ```

3. Tailscale URL only if Hermes dashboard auth is configured via `hermes dashboard register` or DashboardAuthProvider plugin

## Hermes Launcher Fix on Oracle Linux ARM

After `curl install.sh | bash`, fix the shebang:
```bash
sed -i 's|#!/usr/bin/env python3|#!/home/opc/.hermes/hermes-agent/venv/bin/python3|' ~/.hermes/hermes-agent/hermes
chmod +x ~/.hermes/hermes-agent/hermes
```

## PATH Setup

The installer does not add Hermes to `.bashrc`. Always append:
```bash
echo 'export PATH=$HOME/.hermes/hermes-agent:$HOME/.hermes/bin:$HOME/.local/bin:$PATH' >> ~/.bashrc
```
