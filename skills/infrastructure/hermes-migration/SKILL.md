---
name: hermes-migration
description: Clone a Hermes install between hosts, incl. Docker source.
---

# hermes-migration

## When to use
Clone, copy, or migrate a Hermes Agent installation from one machine to another — e.g. moving a Hostinger VPS install onto a fresh Oracle/OCI box, replicating skills/sessions across machines, or rescuing Hermes data out of a Docker container. Covers the non-obvious Docker-containerized source case.

## What "a full Hermes install" is
- Data home: `~/.hermes/` — config.yaml, auth.json, `.env` (secrets), SOUL.md, skills/, sessions/, cron/, state.db, kanban.db, webui/, pairing/ (Tailscale identity), caches/logs.
- Code: `~/.hermes/hermes-agent/` (git repo) and a node runtime `~/.hermes/node/`.
- WebUI app: `~/hermes-webui/` (separate git repo).
- Docker deployment: same layout in the container at `/root/.hermes` (data) and `/opt/hermes` (install). The container's `~/.ssh` is a throwaway filesystem — keys added there are INERT for host-to-host connections.

## Safety model — pick a mode BEFORE touching anything
- **A (recommended, default):** Keep the TARGET's auth.json / .env / pairing (Tailscale identity). Copy only the SOURCE's skills, sessions, cron, config.yaml, SOUL.md, state.db, kanban.db, webui/, pastes/, sandboxes/, shared/, memories/. Use when both machines already have working installs and you want the target's own keys/identity to stay valid.
- **B (full clone):** Overwrite the target entirely with the source, including keys + identity. Destructive to the target's current setup; only when the target is disposable/empty.
- **C (code+data only):** Copy code, skills, sessions; skip all secrets and config.

ALWAYS back up the target first (reversible):
`rsync -a --exclude='/hermes-agent/.git' /home/opc/.hermes/ /home/opc/backups/hermes-pre-migrate.$(date +%Y%m%d_%H%M%S)/`

## Connection paths (get the SOURCE host; never guess it)
1. **Pull (target drives):** add target's pubkey to the SOURCE HOST's `~/.ssh/authorized_keys` (NOT the container's). Then `ssh user@source-host`. Test connectivity without hanging on a password: `ssh -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=12 user@host 'whoami'`.
2. **Push (source drives):** from the source host, pipe data into the target: `... | ssh opc@<target-ip> 'tar -xf -'`. Key the source's pubkey into target's authorized_keys, or temporarily enable PasswordAuthentication (see pitfalls).
3. **Tailscale:** if both are on the same tailnet, use the tailnet hostname/IP — private, no public exposure. `tailscale status` lists peers; `tailscale ip` gives this box's IP.

## KEY TRICK — stream a containerized Hermes without container-side keys
The target can't log into the container, but it CAN log into the SOURCE HOST and run `docker exec`. Stream the data dir over a login shell with tar pipes — no key needed inside the container:
```bash
ssh user@vps-host "docker exec <container> tar -C /root/.hermes -cf - --exclude='.git' ." \
  | tar -C /home/opc/.hermes-incoming -xf -
```
Dry-run first by listing: `ssh user@vps 'docker ps | grep hermes'` then `docker exec <ct> ls /root/.hermes`.
Reusable script: `scripts/pull-docker-hermes.sh`.

## Pitfalls
- **Container vs host:** users often type commands inside the container (`root@<id>`) thinking they're on the host. The container short-ID in the prompt is the tell. Keys added to the container's `~/.ssh` are inert. `exit` out of the container to reach the host.
- **Public key as a command:** a pubkey line `ssh-ed25519 AAAA...` is NOT a command — running it gives `command not found`. It must be appended to a file: `echo 'ssh-ed25519 ...' >> ~/.ssh/authorized_keys`.
- **IPv6 egress:** if the only source address is IPv6, verify the target has global IPv6 egress (`ip -6 addr show ... global`). Cloud boxes (e.g. Oracle OCI) often only have a Tailscale ULA (`fd7a:`) and CANNOT reach a public IPv6 — get the source's IPv4 (`curl -4 ifconfig.me`).
- **sshd dropin ordering:** `PasswordAuthentication` is a single value; later-read dropin files override earlier ones alphabetically. A `50-cloud-init.conf` with `no` can beat your `99-temp-pw.conf` with `yes`. To temporarily allow password auth for a push, neutralize the existing `no` file, not just add a `yes`. Revert afterward. Prefer key auth.
- **Don't guess the host / don't overwrite blindly:** if you have no source host, you cannot proceed — ask. Never fabricate an IP or overwrite a live install without an explicit backup + mode choice.
- **Secrets vs config:** auth.json + .env are the real secrets; SOUL.md/config.yaml carry provider choices. Preserve target identity in mode A.

## Verify after merge
- `hermes --version` (or the hermes binary path) still works.
- `ls ~/.hermes/skills` shows the source's skills merged.
- Sessions/cron present: check `~/.hermes/sessions`, `~/.hermes/cron`.
- Keys still valid (target's own, in mode A): a quick provider ping.
- Rollback if wrong: `rsync -a /home/opc/backups/hermes-pre-migrate.<ts>/ /home/opc/.hermes/`.
