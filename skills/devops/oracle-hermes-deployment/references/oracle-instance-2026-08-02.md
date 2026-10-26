# Oracle Instance Notes — 2026-08-02

## Instance
- Hostname: instance-20260802-0122
- IP: 137.23.36.156
- User: opc
- Arch: aarch64 (ARM64)
- OS: Oracle Linux 9 (ol)

## Disk Layout
- Disk: /dev/sda, 150 GiB
- PV: /dev/sda3 (Linux LVM)
- VG: ocivolume
- LV: root (/dev/mapper/ocivolume-root), ~133 GiB usable
- FS: XFS

## SSH
- Key: /opt/data/oracle_key (RSA 4096)
- Authorized key: ssh-rsa AAAA... (Hermes container access)
- User public key also added for Windows access.

## Hermes
- Install: `~/.hermes/hermes-agent` (git clone, depth 1)
- Python venv: `~/.hermes/hermes-agent/.venv` (Python 3.11.x via uv)
- Launcher A: `~/.hermes/hermes-agent/hermes` — must point to `.venv/bin/python3`
- Launcher B: `~/.local/bin/hermes` — must also be patched to `.venv/bin/python3`
- PATH: set in both `.bashrc` and `.bash_profile`; login shells need `.bash_profile`
- Version: v0.19.1
- Dashboard: `hermes dashboard --port 9120 --host 127.0.0.1` (SSH tunnel required from Windows)
- Backend: `hermes serve --host 127.0.0.1`
- Note: venv is `.venv` (dot-prefixed), not `venv`

## Outreach Stack
- Location: ~/outreach/ (tarred from container)
- X poster: scripts/x_poster.js — patched from hardcoded /opt/data/node_modules to require('playwright')
- Playwright: installed via npx playwright install chromium, cached at ~/.cache/ms-playwright/

## Tailscale
- Tailscale IP: 100.93.145.31
- Tailscale hostname: instance-20260802-0122.tail2dfc33.ts.net
- Serve enabled: yes (dashboard at port 9120)
- Note: Dashboard host-header check blocks direct Tailscale serve access; use SSH tunnel instead.

## Known Issues
- Hermes dashboard rejects Host header from reverse proxy; SSH port forwarding is the reliable path.
- Oracle df shows stale 100% after cleanup; use du + write-test + df -i to verify real state.
