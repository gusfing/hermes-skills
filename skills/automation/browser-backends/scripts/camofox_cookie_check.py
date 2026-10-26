from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path('/opt/data/.camofox/cookies')
TRACKER_GLOB = '*.json'
AUTH_COOKIE_HINTS = ('auth_token', 'li_at', 'li_rm', 'session')
EARLY_WARN_WINDOW_DAYS = int(os.environ.get('CAMOFOX_COOKIE_EARLY_WARN_DAYS', '7'))


def _parse_ts(val):
    if val is None:
        return None
    try:
        return datetime.fromtimestamp(int(val), tz=timezone.utc)
    except Exception:
        return None


def _load_tracker(path: Path):
    try:
        data = json.loads(path.read_text())
    except Exception:
        return None
    return data


def _warn_delta(delta):
    delta = abs(delta)
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f'{days}d {hours}h {minutes}m'
    if hours > 0:
        return f'{hours}h {minutes}m'
    return f'{minutes}m'


def _classify_alert(expires_at, now):
    if expires_at is None:
        return 'session'
    delta = expires_at - now
    if delta.total_seconds() < 0:
        return 'expired'
    early = delta < __import__('datetime').timedelta(days=EARLY_WARN_WINDOW_DAYS)
    if early:
        return 'expiring_soon'
    return 'ok'


def run() -> None:
    now = datetime.now(timezone.utc)
    findings = []

    for path in sorted(STATE_DIR.glob(TRACKER_GLOB)):
        tracker = _load_tracker(path)
        if not tracker:
            continue
        account = tracker.get('account', path.stem)
        domain = tracker.get('domain', 'unknown')
        cookies = tracker.get('cookies') or []
        auth_names = [c['name'] for c in cookies if any(h in c.get('name', '').lower() for h in AUTH_COOKIE_HINTS)]
        if not auth_names:
            auth_names = sorted({c['name'] for c in cookies})

        worst = None
        worst_score = None
        for cookie in cookies:
            expires_at = _parse_ts(cookie.get('expires_unix' ))
            if expires_at is None:
                candidate = ('session', expires_at, cookie['name'])
            else:
                cand_delta = expires_at - now
                score = cand_delta.total_seconds()
                if worst_score is None or score < worst_score:
                    worst_score = score
                    worst = ('expiring_soon' if cand_delta >= __import__('datetime').timedelta(0) and cand_delta < __import__('datetime').timedelta(days=EARLY_WARN_WINDOW_DAYS) else ('expired' if cand_delta.total_seconds() < 0 else 'ok'), expires_at, cookie['name'])

        if worst is None:
            worst = ('session', None, auth_names[0] if auth_names else 'unknown')

        alert, expires_at, name = worst
        findings.append({
            'account': account,
            'domain': domain,
            'alert': alert,
            'cookie_name': name,
            'auth_cookies': auth_names,
            'expires_at': expires_at.isoformat() if isinstance(expires_at, datetime) else None,
        })

    print(json.dumps({'checked_at': now.isoformat(), 'accounts': findings}, indent=2))


if __name__ == '__main__':
    run()
