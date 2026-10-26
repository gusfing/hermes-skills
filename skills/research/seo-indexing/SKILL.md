---
name: seo-indexing
description: Use when submitting a fresh URL for fast indexing.
---

# SEO Fast Indexing

> "Publishing without indexing is printing flyers and leaving them in your
> garage."

Push every fresh URL while the topic is still hot. This is the step that turns a
content machine into a ranking machine: trend found → content drafted → page
indexed, all inside one day.

## BLOCKING PREREQUISITE

**No paid indexing API credential exists on this machine.** Verified absent:

```bash
grep -ri "indexceptional\|rapidapi" ~/.hermes/config.yaml /home/opc/kawaki-outreach/*.py 2>/dev/null
```

Nothing found. So this skill ships with two honest routes:

### Route A — IndexNow (free, key-free, works now)

IndexNow is open for verification-by-file. For sites on any host that can serve
a file:

1. Verify the site (host a `indexnow-key.txt` or use HTTP verification).
2. On publish, POST the URL to the IndexNow endpoint:

```bash
curl -sS -X POST https://api.indexnow.org/indexnow \
  -H 'Content-Type: application/json' \
  -d '{"host":"kawaki.co.in","key":"<KEY>","urlList":["https://kawaki.co.in/new-page"]}'
```

Response `200` = accepted for submission. `202` = queued. `400` = bad payload,
read `message`. Record the response code. Do not claim submission worked without
it.

`ponytail:` IndexNow covers Bing, Yandex, and the IndexNow partner network. It
does **not** submit to Google's primary index — Google uses its own crawl and
sitemap pipeline. For Google, `robots.txt`, an XML sitemap, and internal linking
still do the work.

### Route B — RapidAPI Indexceptional (needs a key)

If the user pays for Indexceptional, ask for the `x-rapidapi-key` header value
and host. Drop it in a file on disk — never paste into chat. Then:

```bash
curl -sS -X GET "https://indexceptional.p.rapidapi.com/api/v1/index" \
  -H "x-rapidapi-key: <KEY>" \
  --data-urlencode "url=https://kawaki.co.in/new-page"
```

Read the HTTP status. Only report success on a 2xx.

## Procedure (general)

1. **Confirm the URL is actually live** — `curl -sSI <url>` returns 200. Never
   index a URL that 404s or redirects.
2. **Check the page is indexable** — no `noindex`, not blocked in `robots.txt`,
   not canonicalised elsewhere.
3. **Submit**, capture the response code.
4. **Record** in the run log: url, endpoint, timestamp, response code.
5. **Sitemap**: if a new page belongs in `sitemap.xml`, add it. A submitted URL
   not in the sitemap is a warning sign, not a failure.

## Hard rules

- **Never claim a URL was indexed without a 2xx response code.** "Submitted" and
  "indexed" are different claims. Google may still crawl nothing for weeks.
- **Check `noindex` before submitting.** Submitting a noindexed page is wasted.
- **Record the response code, always.** See `evidence-before-claiming`.
