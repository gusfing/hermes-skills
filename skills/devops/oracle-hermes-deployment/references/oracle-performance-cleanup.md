# Oracle Linux performance cleanup recipe

Context: 10G RAM, 133G root volume, Hermes services running. Goal: free space and trim noisy caches without touching active state.

## Verified safe deletions

- `/home/opc/backups/*` — old pre-merge/pre-migration snapshots, safe to delete
- `/home/opc/hermes-install-incoming` — stale install bundle after successful install
- npm cache: `npm cache clean --force`
- dnf cache: `dnf clean all`
- app cache files older than 7 days: Camofox, Playwright, node-gyp, electron
- journal archives: `journalctl --vacuum-size=50M` and `--vacuum-time=2d`

## Kernel tuning

- `sysctl vm.swappiness=10` on machines with ample RAM; default 60 is unnecessary

## Order of operations

1. Check current usage with `du -sh` top dirs
2. Delete stale bundles/backups first
3. Clear package/cache directories
4. Vacuum journals via root
5. Re-check `df -h`

## Notes

- `journalctl --vacuum-size=50M` from non-root can succeed but silently skip `/run/log/journal/*` owned by `systemd-journal`; need `sudo` for real effect.
- Docker errors from `opc` usually mean missing docker group membership, not broken Docker.
- `vm.swappiness` change is runtime-only; add to `/etc/sysctl.d/99-swappiness.conf` to persist.
