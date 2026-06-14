"""
match_schedule.py — Extra Time
Pulls the FIFA World Cup schedule + live match status from football-data.org.

Requires a FREE api key from https://www.football-data.org/client/register
set as the env var / GitHub secret FOOTBALL_DATA_API_KEY.

Status values we care about:
  PAUSED   -> half-time   (post a HALF-TIME reaction)
  FINISHED -> full-time   (post a FULL-TIME reaction)
"""

import os
import requests
from datetime import datetime, timedelta

FD_BASE = "https://api.football-data.org/v4"
COMPETITION = "WC"  # FIFA World Cup


def _headers():
    key = os.environ.get('FOOTBALL_DATA_API_KEY', '')
    return {'X-Auth-Token': key} if key else {}


def has_api_key():
    return bool(os.environ.get('FOOTBALL_DATA_API_KEY', ''))


def get_recent_and_today_matches():
    """
    Return WC matches from yesterday through tomorrow (covers timezones and
    matches in progress). Each match is normalized to a simple dict.
    """
    if not has_api_key():
        print("[match_schedule] No FOOTBALL_DATA_API_KEY set — skipping live matches")
        return []

    today = datetime.utcnow().date()
    date_from = (today - timedelta(days=1)).isoformat()
    date_to   = (today + timedelta(days=1)).isoformat()

    try:
        r = requests.get(
            f"{FD_BASE}/competitions/{COMPETITION}/matches",
            headers=_headers(),
            params={'dateFrom': date_from, 'dateTo': date_to},
            timeout=20,
        )
        if r.status_code == 403:
            print("[match_schedule] 403 — WC may not be in your football-data plan")
            return []
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[match_schedule] Fetch failed: {e}")
        return []

    matches = []
    for m in data.get('matches', []):
        score = m.get('score', {}) or {}
        ft = score.get('fullTime', {}) or {}
        ht = score.get('halfTime', {}) or {}
        home = (m.get('homeTeam', {}) or {}).get('name') or 'Home'
        away = (m.get('awayTeam', {}) or {}).get('name') or 'Away'
        status = m.get('status', '')

        # Use half-time score for HT phase, full-time for FT phase
        matches.append({
            'id':         m.get('id'),
            'status':     status,
            'home':       home,
            'away':       away,
            'home_score': ft.get('home') if ft.get('home') is not None else (ht.get('home') or 0),
            'away_score': ft.get('away') if ft.get('away') is not None else (ht.get('away') or 0),
            'ht_home':    ht.get('home') or 0,
            'ht_away':    ht.get('away') or 0,
            'utc_date':   m.get('utcDate', ''),
        })

    print(f"[match_schedule] {len(matches)} WC matches in window "
          f"({date_from} .. {date_to})")
    return matches


def get_match_events_text(match_id):
    """
    Best-effort: fetch goals + bookings for richer reaction content.
    Returns a short human string, or '' if unavailable (e.g. plan limits).
    """
    if not has_api_key() or not match_id:
        return ''
    try:
        r = requests.get(f"{FD_BASE}/matches/{match_id}",
                         headers=_headers(), timeout=20)
        if r.status_code != 200:
            return ''
        d = r.json()
        bits = []
        for g in (d.get('goals') or [])[:8]:
            scorer = (g.get('scorer', {}) or {}).get('name', '')
            minute = g.get('minute', '')
            if scorer:
                bits.append(f"{scorer} scored ({minute}')")
        for b in (d.get('bookings') or [])[:6]:
            player = (b.get('player', {}) or {}).get('name', '')
            card = b.get('card', '')
            if player and card:
                bits.append(f"{player} {card.replace('_', ' ').lower()}")
        return "; ".join(bits)
    except Exception:
        return ''
