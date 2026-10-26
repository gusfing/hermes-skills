# Oracle Linux Deployment Notes

## Disk expansion procedure
When expanding Oracle Free Tier block volume, the partition/LVM/filesystem do not auto-resize.

### Sequence
1. Resize partition with `fdisk`: delete partition 3, recreate with same start sector and larger end/default last sector.
2. Reread partition table: `sudo partx -u /dev/sda`
3. Resize PV: `sudo pvresize /dev/sda3`
4. Extend LV: `sudo lvextend -l +100%FREE /dev/ocivolume/root`
5. Grow XFS: `sudo xfs_growfs /`

### Verification
```bash
df -h /
df -i /
```

## Inode exhaustion
- Check `df -i` as well as `df -h`; inode exhaustion blocks installs even when disk space shows available.
- Common cause: `node_modules` directories with many small files (e.g. omniroute).
- Fix: remove the offending directory or move it to a different filesystem, then retry.

## Hermes install on Oracle Linux
- Hermes installer prefers Node >=26; if system Node is older, it installs managed Node 22.
- After install, if `hermes` crashes with `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`, the launcher shebang is using system Python 3.9 instead of the venv Python 3.11.
- Fix: `sed -i 's|#!/usr/bin/env python3|#!/home/opc/.hermes/hermes-agent/venv/bin/python3|' ~/.hermes/hermes-agent/hermes`
- `~/.hermes/bin/uv` installs Python into `~/.local/share/uv/python/` and creates the venv at `~/.hermes/hermes-agent/venv/`.

## Tailscale quick install
```bash
curl -fsSL https://tailscale.com/install.sh | sudo sh
sudo systemctl enable --now tailscaled
sudo tailscale up
```

## Disk/inode hygiene before fresh installs
- Clean caches and old installs before retrying: `rm -rf ~/.hermes ~/.claude ~/.cache ~/hermes`
- Re-run installer after freeing inodes.
