---
name: production-nodejs-secret-length-requirements
description: Production Node.js apps often enforce minimum secret lengths at bootstrap and refuse to start with short/default values — diagnosis and fix.
---

# Production Node.js App Secret Length Requirements

## Context

Some production Node.js applications enforce minimum secret lengths at bootstrap time and refuse to start if secrets are too short or use default values. This is a security feature — it prevents operators from accidentally deploying with weak credentials.

The app exits immediately (Docker restart loop), often with a vague error that doesn't immediately point to the secret length.

## OpenWA Example (this session)

OpenWA checks `API_MASTER_KEY` at bootstrap and requires **32+ characters** in production mode. The `.env` file had a short key, causing the container to restart repeatedly:

```
Fatal error during bootstrap — process will exit
Error: Refusing to start in production: insecure or default value for API_MASTER_KEY
(below the 32-character minimum). Set strong, unique secrets (see .env.example).
```

**Fix:**
```bash
# Generate a 64-character hex key
NEW_KEY=$(openssl rand -hex 32)

# Start container with the proper key
docker run -d --name openwa-api -p 127.0.0.1:2785:2785 \
  -e API_MASTER_KEY="$NEW_KEY" \
  -e ENGINE_TYPE=whatsapp-web.js \
  -e PUPPETEER_HEADLESS=true \
  -e DATABASE_TYPE=sqlite \
  -e DATABASE_SYNCHRONIZE=true \
  -v openwa-data:/app/data \
  openwa-openwa:latest
```

## General Pattern

When a Node.js app refuses to start in production mode with an "insecure or default value" error:

### 1. Check the app's bootstrap security code

Look for files named `bootstrap-security.js`, `security-check.js`, or similar in the app's `dist/` directory inside the container or installation:

```bash
docker exec <container> grep -r "minimum\|minLength\|32-character" /app/dist/ 2>/dev/null | head -10
```

### 2. Identify which environment variables are flagged

The error message usually names the specific variable(s) that failed validation. Common candidates:

- `API_MASTER_KEY` / `API_KEY` / `SECRET_KEY`
- `DATABASE_PASSWORD` / `POSTGRES_PASSWORD`
- `JWT_SECRET` / `SESSION_SECRET`
- `ENCRYPTION_KEY` / `CIPHER_KEY`

### 3. Generate compliant secrets

```bash
# 64-character hex key (meets 32-char minimum with room to spare)
openssl rand -hex 32

# 64-character base64 key
openssl rand -base64 48

# 128-character hex key (for high-security apps)
openssl rand -hex 64
```

### 4. Set via environment variable at runtime

Prefer environment variables over `.env` files for secrets — `.env` files often contain short default values that pass development mode checks but fail production:

```bash
docker run -e SECRET="$(openssl rand -hex 32)" ...
```

Or in docker-compose.yml:

```yaml
services:
  app:
    environment:
      - API_MASTER_KEY=${API_MASTER_KEY}  # set from host environment
```

## Detection

When a Docker container restarts repeatedly (`Restarting (1) seconds ago`), check logs immediately:

```bash
docker logs <container_name> --tail 20
```

Look for these keywords:
- "Refusing to start in production"
- "insecure or default value"
- "minimum" / "minLength"
- "bootstrap" + "fatal"

If the container exit code is 1 and logs show a bootstrap security error, the secret length is the most likely cause.

## Prevention

- **Always generate secrets at deployment time**, never rely on `.env` default values for production.
- **Document minimum lengths** in the deployment runbook — if the app enforces a 32-char minimum, generate 64+ char secrets to have margin.
- **Check the app's `.env.example`** — it often documents required variables and their constraints.
