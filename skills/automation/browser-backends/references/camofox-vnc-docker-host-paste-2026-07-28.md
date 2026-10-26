# Camofox VNC: Docker host-paste and launch failure reference

## Observed failure signatures

- `docker: invalid reference format`
- `--name: command not found`
- `-p: command not found`
- `docker: invalid reference format`

These all mean a pasted `docker run --name ... \` block was executed as
one shell line and continuation/newline was lost.

## Container state when VNC is not actually running

- `docker ps` shows container `Up` and ports `6080/9377/4860` bound.
- Inside container: `ps aux` shows no `camofox` server process.
- `/tmp/camofox-server.log` does not exist.
- `http://localhost:9377/health` returns connection reset / empty.

## Intermediate failure: Node REPL instead of script execution

Command:

```bash
docker exec -it ... bash -lc 'CAMOFOX_PORT=9377 ENABLE_VNC=1 NOVNC_PORT=6080 node /opt/data/node_modules/@askjo/camofox-browser/server.js'
```

Returned:

```text
Welcome to Node.js v22.22.3.
Type ".help" for more information.
>
```

Cause: if paste wraps or bash-line break falls before the script path,
`node` can execute without the `.js` target and enter REPL.

Fix: keep the command on one compact line, or use the package wrapper:

```bash
docker exec -it ... /opt/data/node_modules/@askjo/camofox-browser/run.sh
```

## Verified working compose-based setup

Service ports in `docker-compose.yml`:

```yaml
ports:
  - 4860
  - "9377:9377"
  - "6080:6080"
```

Started with:

```bash
docker compose up -d
docker ps --filter name=hermes-agent-zibi-hermes-agent-1
```

Then expected `docker ps` output:

```text
hermes-agent-zibi-hermes-agent-1 Up ... 0.0.0.0:6080->6080/tcp, 0.0.0.0:9377->9377/tcp, 0.0.0.0:32779->4860/tcp
```

## Validated Camofox process list after successful server start

```text
hermes   ... /usr/local/bin/node ... /opt/data/node_modules/@askjo/camofox-browser/server.js ...
```

## Turn-specific note

This session ended before confirming `vnc/status == {"running":true}`;
the next step is launching Camofox interactively from the host, not from
the container's own shell prompt or from the Hermes TUI.
