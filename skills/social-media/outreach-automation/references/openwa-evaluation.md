# OpenWA Evaluation Notes

## Repo
- https://github.com/rmyndharis/OpenWA
- Version seen: 0.12.2
- License: MIT
- Node engines: >=22.13

## Stack
- NestJS + TypeScript backend
- React dashboard
- whatsapp-web.js or Baileys engine
- SQLite/PostgreSQL pluggable storage
- Docker Compose deployment
- Multi-session capable

## Pros
- Full HTTP API + dashboard UI
- Multi-session support
- Rate limiting built in
- Plugins/adapters ecosystem
- Open source, no licensing fees

## Cons for our use case
- Heavy: NestJS build + dependencies
- Requires Docker Compose; cannot run inside this container without host Docker socket
- ~300-500MB RAM per whatsapp-web.js session
- Overkill for single-account outreach
- Windows support exists but less documented

## Ban-risk notes from README
- whatsapp-web.js: lower risk, headless Chromium footprint
- Baileys: higher risk, direct protocol fingerprinting
- Recommended: warm up numbers, avoid cold blasts, rate limit, use dedicated numbers

## Deployment reality
- Cannot run inside this container: no Docker socket mounted
- Best deployed on: host machine, Oracle Free AMD/ARM Linux VM, or any Docker-capable host
- docker-compose v2 required; docker-compose-plugin may not be in all Debian repos

## Local .env template
```env
API_MASTER_KEY=openwa-master-2026
ENGINE_TYPE=whatsapp-web.js
PUPPETEER_HEADLESS=true
NODE_ENV=production
DATABASE_TYPE=sqlite
DATABASE_SYNCHRONIZE=true
```

## Decision
Use OpenWA when:
- User needs full API gateway + multi-session
- Docker Compose is available
- Resource usage is acceptable

Keep lightweight custom stack when:
- Single-account outreach
- Container without Docker socket
- Resource-constrained environment
