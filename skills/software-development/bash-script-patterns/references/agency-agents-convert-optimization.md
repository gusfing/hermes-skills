# agency-agents convert.sh / install.sh optimization notes

Repo: https://github.com/msitarzewski/agency-agents
Agent count: 270 across 18 divisions.
Key scripts: `scripts/convert.sh` (~770 lines), `scripts/install.sh` (~1351 lines).

## What changed

- `convert.sh` now precomputes `name/slug/body` once per source file and passes
  those values into each tool formatter. Converters became pure output writers
  instead of re-reading the same markdown file.
- `install.sh` caches the unified agent file list in `_cache_build()`; all
  division/count/selection functions filter the cache instead of re-scanning.
- Fixed parallel xargs invocation:
  old: `xargs -P N -I {} sh -c '"$SCRIPT" --tool "{}" ...'`
  new: `xargs -P N -I {} bash -c '... "$1" ...' _ {}`

## Verification

- `bash -n scripts/convert.sh`
- `bash -n scripts/install.sh`
- `bash scripts/check-divisions.sh` → 17 divisions consistent
- Full parallel convert: all 14 tools generate 270 outputs with matching counts.

## When to apply this pattern

Any shell-based converter with:
- Multiple target formats from the same source set.
- An outer loop over sources and an inner dispatch over formatters.
- A parallel mode built on `xargs -P` and `bash -c`.

Primary signal: each formatter re-reads the same source file for the same fields.
