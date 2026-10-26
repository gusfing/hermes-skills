# NPM Package Removal Pattern

## Service Deletion Workflow

When removing a globally-installed npm-based service (like 9router):

```bash
# 1. Find running process
ps aux | grep <package-name> | grep -v grep

# 2. Stop the process
kill <PID>

# 3. Uninstall globally
npm uninstall -g <package-name>

# 4. Remove configuration/data directories
rm -rf ~/.<package-name> ~/.npm-global 2>/dev/null || true

# 5. Remove user-local binaries
rm -f ~/.local/bin/<package-name>

# 6. Verify removal
which <package-name> 2>/dev/null || echo "Package not found"
```

## Common Paths to Check

- `~/.local/bin/` - user-installed binaries
- `/usr/local/bin/` - system-level bins
- `~/.npm-global/bin/` - npm prefix bin dir
- `/home/opc/.hermes/node/bin/` - Hermes-managed node

## Pitfall: npm uninstall preserves config

`npm uninstall -g` keeps the package directory in `~/.npm/`. Manually delete with:
```bash
rm -rf ~/.npm/
```

Or use a complete removal pattern:
```bash
npm uninstall -g <package> && rm -rf ~/.npm/ ~/.<package-name>
```