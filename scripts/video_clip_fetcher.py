"""
video_clip_fetcher.py — Extra Time
Fetches FREE, LEGAL football B-roll video clips (generic — crowds, stadiums,
a ball hitting the net, celebrations). NOT match footage.

Sources:
  - Pexels Video API   (free, uses existing PEXELS_API_KEY)
  - Pixabay Video API  (free, needs PIXABAY_API_KEY)

Returns local .mp4 paths. Empty list if no keys / nothing found — callers
fall back to stills only.
"""

import os
import requests

PEXELS_VIDEO  = "https://api.pexels.com/videos/search"
PIXABAY_VIDEO = "https://pixabay.com/api/videos/"

DEFAULT_TIMEOUT = 60
MIN_FILESIZE    = 30000

# Generic football B-roll queries (no players/teams — pure atmosphere)
BROLL_QUERIES = [
    "soccer stadium crowd",
    "football celebration",
    "soccer ball net",
    "stadium floodlights",
    "soccer fans cheering",
    "football pitch",
]


def _download(url, path):
    try:
        r = requests.get(url, timeout=DEFAULT_TIMEOUT, stream=True,
                         headers={'User-Agent': 'ExtraTimeBot/1.0'})
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
        if os.path.getsize(path) < MIN_FILESIZE:
            os.remove(path)
            return False
        return True
    except Exception as e:
        print(f"[broll] Download failed {url[:60]}: {e}")
        if os.path.exists(path):
            try: os.remove(path)
            except: pass
        return False


def _pexels_clips(query, api_key, count=2):
    """Return candidate mp4 URLs from Pexels (prefer portrait / HD-ish)."""
    if not api_key:
        return []
    try:
        r = requests.get(PEXELS_VIDEO,
                         headers={'Authorization': api_key},
                         params={'query': query, 'per_page': count,
                                 'orientation': 'portrait', 'size': 'medium'},
                         timeout=20)
        r.raise_for_status()
        urls = []
        for vid in r.json().get('videos', []):
            files = vid.get('video_files', []) or []
            # Prefer a file roughly 720p-1080p tall to keep downloads light
            files.sort(key=lambda f: abs((f.get('height') or 0) - 1280))
            for f in files:
                link = f.get('link')
                if link:
                    urls.append(link)
                    break
        return urls
    except Exception as e:
        print(f"[broll] Pexels video failed for '{query}': {e}")
        return []


def _pixabay_clips(query, api_key, count=2):
    if not api_key:
        return []
    try:
        r = requests.get(PIXABAY_VIDEO,
                         params={'key': api_key, 'q': query,
                                 'per_page': max(count, 3), 'video_type': 'film'},
                         timeout=20)
        r.raise_for_status()
        urls = []
        for hit in r.json().get('hits', [])[:count]:
            v = hit.get('videos', {}) or {}
            pick = v.get('medium') or v.get('large') or v.get('small') or {}
            if pick.get('url'):
                urls.append(pick['url'])
        return urls
    except Exception as e:
        print(f"[broll] Pixabay video failed for '{query}': {e}")
        return []


def fetch_broll(output_dir, pexels_key=None, pixabay_key=None,
                target_clips=4, queries=None):
    """Download up to target_clips football B-roll mp4s. Returns list of paths."""
    os.makedirs(output_dir, exist_ok=True)
    queries = queries or BROLL_QUERIES
    clips = []
    seen = set()
    idx = 0

    def grab(url, tag):
        nonlocal idx
        if not url or url in seen or idx >= target_clips:
            return
        seen.add(url)
        p = os.path.join(output_dir, f"broll_{idx:02d}_{tag}.mp4")
        if _download(url, p):
            clips.append(p)
            idx += 1

    for q in queries:
        if idx >= target_clips:
            break
        for url in _pexels_clips(q, pexels_key, count=1):
            grab(url, 'px')
        if idx >= target_clips:
            break
        for url in _pixabay_clips(q, pixabay_key, count=1):
            grab(url, 'pb')

    print(f"[broll] Downloaded {len(clips)} B-roll clips")
    return clips
