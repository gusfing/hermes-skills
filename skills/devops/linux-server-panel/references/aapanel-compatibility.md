# aaPanel Compatibility

## Supported Operating Systems (as of 2026)
- Ubuntu
- CentOS
- Debian
- AlmaLinux
- Rocky Linux
- OpenEuler

## Supported Architecture
- **x86_64 only** — no aarch64 / ARM64 build available

## Install Script
`https://www.aapanel.com/install.sh`

Bash script delivered via HTTP. Installs the panel, Nginx/Apache/PHP/MySQL, and sets up the panel web UI on port 8888.

## Result on Oracle Linux 9.8 aarch64

| Check | Result |
|---|---|
| OS | Oracle Linux 9.8 — **NOT in supported list** |
| Architecture | aarch64 (ARM64) — **NOT supported** |
| Install script URL | Reachable (returns 302 redirect to main site) |
| Expected outcome | Install script detects unsupported OS/arch and fails |
| Disk / RAM | 133GB / 10GB — sufficient for the panel itself |

## Observed failure mode on Oracle Linux 9.8 aarch64 (2026-09)

The installer does NOT fail fast on unsupported OS/arch. Actual behavior:

1. `curl -sSO http://www.aapanel.com/script/install.sh` downloads the script (exit 0)
2. `sudo bash install.sh` starts, prints the aaPanel banner, begins downloading
3. Installer downloads a ~70MB Go runtime tarball (`go.tar.gz`) from `https://www.aapanel.com/`
4. After download completes, installer process enters a **frozen state**:
   - CPU at 98.8% (single core) indefinitely
   - Zero progress in `/tmp/aapanel-install.log` (banner only, no download/compile steps)
   - Zero new files created (`/opt/panel`, `/www` never appear)
   - Zero network activity after the Go tarball download
   - No exit — process runs until manually killed
5. After 3+ hours of frozen CPU, the installer had created **nothing** — no panel files, no listening ports, no `/www` directory.

**Bottom line:** On Oracle Linux 9.8 aarch64, the aaPanel installer hangs indefinitely after downloading its Go runtime. It does not error-exit, does not time out, and does not create any panel files. The only resolution is to kill the installer processes.

## Why it hangs

The install script is a generic bash script that downloads and runs the panel installer binary. On unsupported arch (aarch64), the binary either:
- Fails to run but the script doesn't check the exit code, OR
- Enters an infinite loop/compile step that never completes on ARM

Either way, the script does not detect the mismatch and bail — it just spins.

## Notes
- Oracle Linux 9.8 is RHEL-family (dnf/yum available), but aaPanel does not list it.
- aaPanel's install script checks OS via `/etc/os-release` and arch via `uname -m`. If either fails its check, the script exits before installing anything.
- Even on a supported OS, aaPanel's web UI and many of its bundled components (Nginx, PHP-FPM, etc.) are x86_64 binaries. On ARM they would fail to install or run at all.
- If the user needs a web management panel on Oracle Linux + ARM64, **Cockpit** (`dnf install cockpit`, port 9090) is the viable alternative — it's in the Oracle Linux repos, supports aarch64, and covers system overview, terminal, logs, services, storage, network, files, and Podman containers.

## Sources
- aaPanel download page: `https://www.aapanel.com/download.html`
- aaPanel FAQ: "What operating systems does aaPanel support?" — lists Ubuntu, CentOS, Debian, AlmaLinux, Rocky Linux, OpenEuler
