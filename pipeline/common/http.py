"""Shared polite HTTP helper with retry. SEC requires a descriptive User-Agent and
rate-limits ~10 req/s; we stay well under."""
from __future__ import annotations
import json, time, urllib.request, urllib.error

USER_AGENT = "FamilyOfficeResearch adeen@digitalanchormedia.com"
_LAST = [0.0]
_MIN_GAP = 0.15  # seconds between requests


def _throttle():
    dt = time.monotonic() - _LAST[0]
    if dt < _MIN_GAP:
        time.sleep(_MIN_GAP - dt)
    _LAST[0] = time.monotonic()


def fetch(url, accept="application/json", tries=3, timeout=30):
    last = None
    for i in range(tries):
        _throttle()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 429, 500, 502, 503):
                time.sleep(1.5 * (i + 1)); continue
            raise
        except Exception as e:
            last = e
            time.sleep(1.0 * (i + 1))
    raise last


def fetch_json(url, **kw):
    return json.loads(fetch(url, accept="application/json", **kw))
