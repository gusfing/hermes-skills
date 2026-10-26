#!/usr/bin/env python3
"""Launch Chrome with CDP on the VNC desktop and wait for it to be reachable.

Use this when Chrome keeps dying in background terminals — this script
launches Chrome via subprocess.Popen with the correct DISPLAY/XAUTHORITY
env vars, waits up to 30s for CDP to come up, and reports health.

Usage:
    python3.12 launch-chrome-cdp.py

Requires: DISPLAY=:1, XAUTHORITY=/home/opc/.Xauthority,
           DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus,
           HOME=/home/opc
"""
import os
import sys
import json
import time
import socket
import subprocess
import urllib.request

os.environ.setdefault("DISPLAY", ":1")
os.environ.setdefault("XAUTHORITY", "/home/opc/.Xauthority")
os.environ.setdefault("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1000/bus")
os.environ.setdefault("HOME", "/home/opc")

CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
USER_DATA_DIR = "/home/opc/chrome-vnc-profile"
LOG_PATH = "/tmp/chrome-vnc.log"
CHROME_BIN = "/usr/bin/google-chrome-stable"


def kill_stale():
    """Kill any stale Chrome instances using our user-data-dir."""
    subprocess.run(["pkill", "-9", "-f", "chrome.*vnc-profile"],
                   capture_output=True)
    time.sleep(2)


def port_free(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        return result != 0
    except Exception:
        return True


def launch_chrome():
    log_f = open(LOG_PATH, "w")
    proc = subprocess.Popen(
        [CHROME_BIN,
         "--remote-debugging-port=%d" % CDP_PORT,
         "--remote-debugging-address=0.0.0.0",
         "--user-data-dir=%s" % USER_DATA_DIR,
         "--no-first-run",
         "--no-default-browser-check",
         "--disable-gpu",
         "--disable-dev-shm-usage",
         "--no-sandbox",
         "--disable-software-rasterizer",
         "--no-zygote"],
        env=os.environ,
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )
    print(f"Chrome PID: {proc.pid}")
    return proc, log_f


def wait_for_cdp(timeout=30):
    """Poll CDP until /json/version responds or timeout."""
    for i in range(timeout):
        time.sleep(1)
        try:
            req = urllib.request.Request(
                f"{CDP_URL}/json/version",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2) as r:
                data = json.loads(r.read())
                ws = data.get("webSocketDebuggerUrl", "?")
                browser = data.get("Browser", "?")
                print(f"✅ CDP UP after {i+1}s: {browser} | WS: {ws[:60]}")
                # List tabs
                tabs_req = urllib.request.urlopen(f"{CDP_URL}/json", timeout=2)
                tabs = json.loads(tabs_req.read())
                print(f"   Tabs ({len(tabs)}):")
                for t in tabs[:5]:
                    print(f"     {t.get('title','?')[:30]} | {t.get('url','?')[:50]}")
                return True
        except Exception:
            if i % 5 == 0 and i > 0:
                print(f"  .{i}s waiting for CDP...")
            # Check if Chrome died
            if proc.poll() is not None:
                print(f"❌ Chrome died after {i+1}s, exit code: {proc.returncode}")
                with open(LOG_PATH) as f:
                    print("   Log tail:", f.read()[-300:])
                return False
    print(f"❌ Chrome failed to start CDP within {timeout}s")
    return False


if __name__ == "__main__":
    print(f"DISPLAY={os.environ['DISPLAY']}")
    print(f"XAUTHORITY={os.environ['XAUTHORITY']}")
    print(f"HOME={os.environ['HOME']}")

    print("\n--- Killing stale Chrome ---")
    kill_stale()

    print("\n--- Port check ---")
    if not port_free(CDP_PORT):
        print(f"❌ Port {CDP_PORT} still in use — kill stale Chrome first")
        sys.exit(1)
    print(f"✅ Port {CDP_PORT} free")

    print("\n--- Launching Chrome ---")
    proc, log_f = launch_chrome()

    print("\n--- Waiting for CDP (30s) ---")
    if not wait_for_cdp(30):
        sys.exit(1)

    print("\n✅ Chrome CDP ready at", CDP_URL)
