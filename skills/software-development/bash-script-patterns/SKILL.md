---
name: bash-script-patterns
description: "Bash bulk-file optimization and safe parallel xargs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [bash, shell, scripting, optimization, parallel, xargs, quoting, find, awk, performance]
    related_skills: [simplify-code, github-pr-workflow, requesting-code-review]
---

# Bash Script Patterns — Optimizations & Pitfalls

Reusable patterns for high-quality bash scripts, focused on performance
in bulk-file pipelines and safe parallel execution.

## When to Use

Use this skill when:
- Optimizing shell scripts that process many files or many target formats.
- Converting/transforming large file sets with repeated `find`/`awk` calls.
- Using `xargs -P` for parallelism.
- Debugging silent argument loss in `bash -c` / `sh -c` wrappers.
- Auditing a repo's conversion/install/build scripts for unnecessary disk scans.

## 1. Single-Pass Bulk File Processing

**Problem:** A conversion loop scans the same 258-agent, 18-division tree once per
target tool, resulting in ~4,600 redundant `find`/`head`/`awk` calls for a full
run.

**Fix:** Scan source files once, parse shared fields up front, dispatch to all
formatters from the in-memory tuple.

```bash
for dir in "${AGENT_DIRS[@]}"; do
  while IFS= read -r -d '' file; do
    name="$(get_field "name" "$file")"
    [[ -z "$name" ]] && continue
    slug="$(slugify "$name")"
    body="$(get_body "$file")"

    case "$tool" in
      gemini-cli)  write_gemini_cli  "$slug" "$body" ;;
      opencode)    write_opencode    "$name" "$slug" "$body" ;;
      cursor)      write_cursor      "$slug" "$description" ;;
      ...
    esac
  done < <(find "$dir" -name "*.md" -type f -print0 | sort -z)
done
```

**Why it wins:** File metadata and frontmatter parsing dominate; duplicating that
work 14× for 14 tools is pure waste. Precompute `name/slug/body/description` once
and pass as args; individual formatters become pure output writers.

**Caveat:** If a formatter needs additional frontmatter fields it doesn't share
with others, parse just those extras inline — but don't re-parse `name`/`body`.

## 2. Caching Division/Agent File Lists

**Problem:** `division_files()`, `division_count()`, `build_selection()`, and
`selected_agent_count_all()` each call `find` per division on demand. Interactive
wizards and `--list` paths re-scan the same tree dozens of times per run.

**Fix:** Build one file list once, filter it in memory.

```bash
_AGENT_FILE_CACHE=()
_DIV_SLUGS=""
_DIV_COUNT=0

_cache_build() {
  [[ -n "${_AGENT_FILE_CACHE:-}" ]] && return
  local slug file
  for div in "${ALL_DIVISIONS[@]}"; do
    while IFS= read -r -d '' file; do
      is_agent_file "$file" || continue
      slug="$(agent_slug "$file")"
      [[ -z "$slug" ]] || _AGENT_FILE_CACHE+=("$file")
      [[ -n "$slug" ]] && _DIV_SLUGS+="$slug"$'\n'
      (( _DIV_COUNT++ )) || true
    done < <(find "$REPO_ROOT/$div" -name "*.md" -type f -print0 2>/dev/null)
  done
}

division_count()    { _cache_build; echo "$_DIV_COUNT"; }
division_files()    { _cache_build; ...filter _AGENT_FILE_CACHE... ; }
build_selection()   { _cache_build; ...filter _AGENT_FILE_CACHE... ; }
selected_agent_count_all() { _cache_build; echo "$_DIV_COUNT"; }
```

**Why it wins:** One `find` walk per run instead of N+ walks. Interactive paths
benefit most because they previously re-counted on every screen refresh.

## 3. Safe Parallel `xargs` with `bash -c`

**Problem:** `xargs -P ... -I {} sh -c 'cmd {}'` silently drops the positional
argument on Linux because `sh -c` positional handling differs from `bash -c`.

**Broken:**
```bash
printf '%s\n' "${tools[@]}" | xargs -P 4 -I {} sh -c '"$SCRIPT" --tool "{}" --out "$OUT"'
# {} may be empty inside sh -c; no output is written.
```

**Fix:** Use `bash -c` with positional params and supply `_` as `$0`:
```bash
printf '%s\n' "${tools[@]}" | xargs -P 4 -I {} bash -c '
  "$AGENCY_CONVERT_SCRIPT" --tool "$1" --out "$AGENCY_CONVERT_OUT" \
    > "$AGENCY_CONVERT_OUT_DIR/$1" 2>&1
' _ {}
```

**Why it works:** `bash -c '...' _ {}` sets `$0=_`, `$1=toolname`. The
redirection target `$1` is then populated. Always verify parallel mode by
checking output file counts match single-tool runs.

## 4. Bash Function Argument Conventions

When refactoring a function to take precomputed arguments instead of re-parsing
its file:

```bash
# Before: converter re-reads file each time
convert_foo() {
  local file="$1"
  local name; name="$(get_field "name" "$file")"
  local body; body="$(get_body "$file")"
  ...
}

# After: caller does the I/O once
convert_foo() {
  local file="$1" name="$2" slug="$3" body="$4"
  local description; description="$(get_field "description" "$file")"
  ...
}
```

**Rule:** If a function is called N times per loop and always reads the same
fields from the same file, those reads belong outside the function. The function
becomes a pure formatter.

## 5. Verification After Refactoring Shell Scripts

When changing argument flow or output structure in `bash`:

1. `bash -n script.sh` — syntax check.
2. Single-tool dry run: `bash scripts/convert.sh --tool <one>`; count outputs.
3. Full parallel run: `bash scripts/convert.sh --parallel`; compare counts.
4. If counts diverge, inspect the per-tool log for missing outputs before
   declaring success.

Do not trust a zero exit code alone; count verification catches silent drops.

## Pitfalls

- **xargs -I {} with sh -c drops {} on Linux.** Always use `bash -c '... "$1" ...' _ {}`.
- **Re-parsing files inside inner loops.** If a loop body reads the same file
  N times for N formatters, move the read outside the loop.
- **Cache invalidation.** If source files change mid-run, a cache built at the
  top of the script is stale. For short-lived scripts this is fine; for watchers
  or long-lived processes, invalidate on file mtime change.
- **Assuming `find` order is stable across filesystems.** Sort with `sort -z`
  when deterministic output matters.
- **`set -e` and arithmetic.** `(( count++ ))` returns 1 when `count` was 0.
  Use `(( count++ )) || true` or `count=$(( count + 1 ))` under `set -e`.

## Related

- `simplify-code` — parallel reviewer fan-out for code cleanup.
- `github-pr-workflow` — PR lifecycle, including script CI checks.
- `systematic-debugging` — when refactored scripts misbehave.
