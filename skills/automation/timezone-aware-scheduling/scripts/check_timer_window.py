#!/usr/bin/env python
"""Prove a systemd timer's OnCalendar schedule is what it looks like.

Why this exists: `systemd-analyze calendar` prints only the NEXT elapse, so it
CANNOT prove a window is covered -- counting its output gives 1 even for a
correct every-30-min spec. That led to a confident, completely wrong
"it only fires once a day" conclusion. `Normalized form` is the ground truth.

This reads the live unit back with `systemctl cat`, normalises every
OnCalendar line, and reports the next fire converted to the audience zone.

    python check_timer_window.py x-daily.timer li-engage.timer

Exit code 0 if every non-empty line parsed. Non-zero if any line is invalid,
the list is empty, or a timer is not armed.
"""
import subprocess
import sys
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def calendar_lines(unit):
    out = subprocess.run(["systemctl", "--user", "cat", unit],
                         capture_output=True, text=True).stdout
    return [ln.split("=", 1)[1].strip()
            for ln in out.splitlines() if ln.startswith("OnCalendar=")]


def normalize(spec):
    r = subprocess.run(["systemd-analyze", "calendar", spec],
                       capture_output=True, text=True)
    txt = r.stdout + r.stderr
    for ln in txt.splitlines():
        if "Normalized" in ln:
            return True, ln.split("form:")[1].strip()
    return False, (txt.strip().splitlines() or ["?"])[-1][:70]


def next_fire(unit):
    out = subprocess.run(["systemctl", "--user", "show", unit,
                          "-p", "NextElapseUSecRealtime", "--value"],
                         capture_output=True, text=True).stdout.strip()
    if not out or out == "n/a":
        return None
    try:
        d = datetime.strptime(out.replace("GMT", "").strip(),
                              "%a %Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return d.replace(tzinfo=timezone.utc)


def trigger(unit):
    out = subprocess.run(["systemctl", "--user", "show", unit,
                          "-p", "Trigger", "--value"],
                         capture_output=True, text=True).stdout.strip()
    return out


def main(units):
    bad = 0
    for unit in units:
        specs = calendar_lines(unit)
        if not specs:
            print(f"{unit}: NO OnCalendar lines at all")
            bad += 1
            continue
        print(f"{unit}:")
        for s in specs:
            if not s:
                print("    (reset)")
                continue
            ok, info = normalize(s)
            print(f"    {s!r}")
            print(f"      -> {'OK  ' if ok else 'BAD '} {info}")
            if not ok:
                bad += 1
        # an empty list means nothing scheduled at all
        if not [s for s in specs if s]:
            print("    WARNING: list is empty (reset line with no entries) "
                  "-- timer will never fire")
            bad += 1
        nf = next_fire(unit)
        if nf is None:
            print("    next fire: NONE")
            bad += 1
        else:
            print(f"    next {nf:%H:%M} UTC = "
                  f"{nf.astimezone(IST):%H:%M} IST")
        t = trigger(unit)
        if t in ("n/a", ""):
            print("    Trigger: n/a -- NOT armed, will never fire")
            bad += 1
        print()
    return 1 if bad else 0


if __name__ == "__main__":
    argv = sys.argv[1:] or ["x-daily.timer", "li-engage.timer"]
    sys.exit(main(argv))
