# aaPanel on Oracle Linux 9.8 aarch64 — installation failure

Session: Sept 21, 2026
Target: 137.23.36.156 (Oracle Linux Server 9.8, aarch64, 10GB RAM, 133GB disk)
Installer: `https://www.aapanel.com/script/install.sh` (downloaded to /tmp/install.sh, run via `sudo bash install.sh`)

## What happened

1. Downloaded install.sh (~30KB shell script)
2. Started `sudo bash install.sh` in background
3. Installer downloaded a 70MB Go runtime tarball: `/tmp/go.tar.gz` (70,250,819 bytes, dated Oct 1 2024)
4. After download, installer process entered a frozen state:
   - PID 1425792: state `R` (running), 3h28m of CPU time (11,179s user + 1,239s system)
   - 4 installer processes total, all root-owned
   - Zero network activity (no connections to download servers)
   - No new files created (no `/opt/panel`, no `/www`, no panel binaries)
   - Log file `/tmp/aapanel-install.log` contained only the aaPanel banner — no progress, no errors
   - 98.8% CPU usage continuously for the duration
5. After 206 minutes, installer was killed (root-owned processes required sudo; `sudo kill -9` succeeded)

## Result

- No panel installed anywhere
- `/opt/panel/` does not exist
- `/www/` does not exist
- No ports listening (8888, 41308 — nothing)
- No panel binary or config created

## Conclusion

aaPanel's install.sh does not work on Oracle Linux 9.8 aarch64. The Go tarball download succeeded but the post-download installation phase hung indefinitely. This matches the known compatibility warning: aaPanel does not support Oracle Linux or aarch64.

## What worked instead

Cockpit was already installed on the server (just not enabled). Activated via:
```
sudo systemctl enable --now cockpit.socket
```

Exposed publicly via nginx on port 80 (panel.kawaki.co.in), with basic auth using openssl-generated htpasswd (since `htpasswd` binary was not available).

## Recovery steps if aaPanel installer hangs again

```bash
# Find installer PIDs
ps aux | grep install.sh | grep -v grep

# Kill them (requires sudo for root-owned processes)
sudo kill -9 <PID1> <PID2> ...

# Check if anything was partially installed
ls /opt/panel/ /www/ 2>&1

# Clean up
rm -f /tmp/install.sh /tmp/aapanel-install.log /tmp/go.tar.gz

# Fall back to Cockpit
sudo systemctl enable --now cockpit.socket
```
