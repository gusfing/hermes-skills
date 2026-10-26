# computer_use on Linux VNC — DISPLAY propagation fix

## Problem

cua-driver captures return 0×0 or empty AX tree on Linux with VNC running, even though VNC is healthy. Root cause: cua-driver inherits its environment from the Hermes gateway process, and if the gateway runs as a systemd service without `DISPLAY=:1`, cua-driver has no X11 display to attach to.

## Diagnosis

```bash
# Check if gateway has DISPLAY
cat /proc/<gateway-pid>/environ | tr '\0' '\n' | grep DISPLAY
# Empty = problem

# Check if cua-driver has DISPLAY
cat /proc/<cua-driver-pid>/environ | tr '\0' '\n' | grep DISPLAY
# Empty = inherited from gateway without DISPLAY
```

## Fix

Add `Environment="DISPLAY=:1"` to the systemd service file in BOTH locations:

1. `~/.config/systemd/user/hermes-gateway.service` (user-level)
2. `/etc/systemd/user/hermes-gateway.service` (system-level override)

Both matter — systemd merges them and system-level can override user-level.

```ini
[Service]
Environment="DISPLAY=:1"
```

Then restart the gateway. From inside the gateway process, `systemctl restart` is blocked. Options:
- **From separate SSH session:** `hermes gateway restart`
- **From inside (no separate session):** `kill -9 <gateway-pid>` — systemd auto-restarts with new env

## Verification

After restart, verify cua-driver inherited DISPLAY:
```bash
cat /proc/<cua-driver-pid>/environ | tr '\0' '\n' | grep DISPLAY
# Should show DISPLAY=:1
```

Then test: `computer_use capture mode=som` should return a real 1920×1080 screenshot with AX elements, not 0×0.

## Fallback when computer_use still can't see

If after DISPLAY fix capture still fails, use PIL screenshot + vision_analyze:
```bash
export DISPLAY=:1
python3 -c "from PIL import ImageGrab; ImageGrab.grab().save('/tmp/vnc.png')"
# vision_analyze /tmp/vnc.png
```

This gives desktop visibility without full computer_use.

## Related

- See `computer-use-linux-vnc` skill for full class-level guidance
- See `browser-backends` skill for Chrome CDP / browser automation patterns
- See `oracle-hermes-deployment` skill for server setup (VNC, 9router, etc.)
