# Session Notes: 9router + Carousel Generation

## 9router Image Provider Status

**Finding:** Image catalog is empty (`{"object":"list","data":[]}`) even when endpoint exists.

**Actual State Found:**
- `providerNodes` table: EMPTY (no provider nodes registered)
- `providerConnections` table contains 2 entries: 401 (ollama bad key) and 402 (OpenRouter credits exhausted)
- Catalog shows `gemini-3.1-flash-image`, `flux` etc. but they're not USEFUL without credentials

**Error Code Reference:**
| Code | Provider | Message |
|------|----------|---------|
| 402 | openrouter | "Insufficient credits. This account never purchased credits" |
| 401 | ollama | "Unauthorized" (bad API key) |

**Diagnostic SQL:**
```sql
SELECT provider, name, isActive, lastError, errorCode FROM providerConnections;
```

**Resolution paths:**
1. **OpenRouter**: Add credits at https://openrouter.ai/settings/credits
2. **Any provider**: 402 = needs funding, 401 = bad key, 403 = rate limited
3. **No providers**: Add credentials via 9Router dashboard -> Media Providers

## html-to-carousel Installation Issue

**GitHub clone failed:** `fatal: could not read Username for 'https://github.com': No such device or address`

**Workaround:** Install locally from source mirror or use alternative HTML-to-image renderer.

**Required for carousel generation:** Tool must be installed at `/tmp/html-to-carousel/`.

## Key Files
- 9router DB: `~/.9router/db/data.sqlite` (table `apiKeys` contains valid key)
- Model catalog: `~/.9router/model-catalog.json` (lists models but credentials control usability)