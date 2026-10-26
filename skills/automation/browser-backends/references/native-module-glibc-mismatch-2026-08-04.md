# better-sqlite3 glibc mismatch on Oracle Linux 9 aarch64

## Symptom
`better-sqlite3` loads the wrong binary on Oracle Linux 9 aarch64.

## Observed error
```
/lib64/libm.so.6: version `GLIBC_2.38' not found (required by .../better-sqlite3/prebuilds/linux-arm64.node)
```

## Host state
- OS: Oracle Linux 9 aarch64
- glibc: 2.34
- Target prebuilt requires: glibc 2.38

## Affected packages
- `@askjo/camofox-browser` -> browser warm/launch fails
- `omniroute` -> HTTP 500 on all endpoints
- Any npm package depending on `better-sqlite3` with the same prebuilt

## Failed repair attempts
1. `npm rebuild better-sqlite3` -> succeeds but still loads incompatible prebuilt
2. `npm rebuild --build-from-source` -> succeeds but does not produce a local `.node`
3. Installing `sqlite-devel` + `gcc` + `make` + `python3-devel` -> still no local `better_sqlite3.node`
4. `node -e "require('better-sqlite3')"` -> succeeds after rebuild, but the process still crashes at runtime because the loaded binary path is the same prebuilt

## Decision rule
On this host class, treat `better-sqlite3` as a hard blocker for Camofox/OmniRoute unless the package author ships a glibc-compatible build or the module is patched out. Do not spend further session time retrying `npm rebuild` variations.

## Preferred path
Use Google Chrome Stable + CDP + `browser-harness` instead. That path does not depend on `better-sqlite3`.

## Docker caveat
Even Docker is not automatically viable if the image is amd64-only. Only use multi-arch images or images already present on this host.