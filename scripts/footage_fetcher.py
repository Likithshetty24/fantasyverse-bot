"""
footage_fetcher.py
Real anime artwork from Jikan (MyAnimeList) — free, no API key.
Falls back to Pexels generic queries if PEXELS_API_KEY is set
and Jikan returns too few images.
"""

import os
import re
import time
import requests

JIKAN_SEARCH = "https://api.jikan.moe/v4/anime"
JIKAN_TOP    = "https://api.jikan.moe/v4/top/anime"
PEXELS_API   = "https://api.pexels.com/v1"

# Map common anime keywords to specific MAL search titles
KEYWORD_MAP = {
    'dragon ball':    ['Dragon Ball Super', 'Dragon Ball Z'],
    'one piece':      ['One Piece'],
    'naruto':         ['Naruto', 'Boruto'],
    'attack on titan':['Attack on Titan'],
    'demon slayer':   ['Demon Slayer'],
    'my hero':        ['My Hero Academia'],
    'jujutsu':        ['Jujutsu Kaisen'],
    'bleach':         ['Bleach'],
    'chainsaw man':   ['Chainsaw Man'],
    'spy x family':   ['Spy x Family'],
    'vinland':        ['Vinland Saga'],
    'overlord':       ['Overlord'],
    're:zero':        ['Re:Zero'],
    'sword art':      ['Sword Art Online'],
    'hunter x hunter':['Hunter x Hunter'],
    'frieren':        ['Frieren'],
    'solo leveling':  ['Solo Leveling'],
    'blue lock':      ['Blue Lock'],
    'mashle':         ['Mashle'],
}

FALLBACK_TITLES = [
    'Jujutsu Kaisen',
    'Demon Slayer',
    'My Hero Academia',
    'One Piece',
    'Chainsaw Man',
    'Solo Leveling',
    'Frieren',
]


# ---------------------------------------------------------------------------
# Jikan (MyAnimeList)
# ---------------------------------------------------------------------------

def _jikan_search(query, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(
                JIKAN_SEARCH,
                params={'q': query, 'limit': 5, 'order_by': 'score', 'sort': 'desc'},
                timeout=15,
            )
            if r.status_code == 429:
                time.sleep(2)
                continue
            r.raise_for_status()
            urls = []
            for entry in r.json().get('data', []):
                large = entry.get('images', {}).get('jpg', {}).get('large_image_url')
                if large:
                    urls.append(large)
            return urls
        except Exception as e:
            print(f"[footage_fetcher] Jikan failed for '{query}': {e}")
            time.sleep(1)
    return []


def _jikan_top(limit=10):
    try:
        r = requests.get(JIKAN_TOP, params={'limit': limit}, timeout=15)
        r.raise_for_status()
        urls = []
        for entry in r.json().get('data', []):
            large = entry.get('images', {}).get('jpg', {}).get('large_image_url')
            if large:
                urls.append(large)
        return urls
    except Exception as e:
        print(f"[footage_fetcher] Jikan top failed: {e}")
        return []


def _extract_anime_titles(news_items):
    queries = []
    for item in news_items:
        text = (item['title'] + ' ' + item.get('summary', '')).lower()
        matched = False
        for keyword, titles in KEYWORD_MAP.items():
            if keyword in text:
                queries.extend(titles)
                matched = True
                break
        if not matched:
            cap = re.search(r'\b([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)+)\b', item['title'])
            if cap:
                queries.append(cap.group(1))
            else:
                queries.append('anime')
    return queries


# ---------------------------------------------------------------------------
# Pexels (fallback)
# ---------------------------------------------------------------------------

def _pexels_search(query, api_key, count=2):
    if not api_key:
        return []
    try:
        r = requests.get(
            f"{PEXELS_API}/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": count, "orientation": "portrait", "size": "large"},
            timeout=15,
        )
        r.raise_for_status()
        return [p['src']['large2x'] for p in r.json().get('photos', [])]
    except Exception as e:
        print(f"[footage_fetcher] Pexels failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------

def _download_image(url, path):
    try:
        r = requests.get(url, timeout=20, stream=True)
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"[footage_fetcher] Download failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def fetch_footage(news_items, output_dir, pexels_key=None, target_count=12):
    os.makedirs(output_dir, exist_ok=True)
    downloaded = []
    seen = set()
    idx = 0

    # Primary: Jikan
    queries = _extract_anime_titles(news_items) + FALLBACK_TITLES
    for q in queries:
        if idx >= target_count:
            break
        for url in _jikan_search(q):
            if idx >= target_count or url in seen:
                continue
            seen.add(url)
            p = os.path.join(output_dir, f"img_{idx:03d}.jpg")
            if _download_image(url, p):
                downloaded.append(p)
                idx += 1
        time.sleep(0.4)  # Jikan rate-limit politeness

    # Top up with Jikan top anime
    if idx < target_count:
        for url in _jikan_top(20):
            if idx >= target_count or url in seen:
                continue
            seen.add(url)
            p = os.path.join(output_dir, f"img_{idx:03d}.jpg")
            if _download_image(url, p):
                downloaded.append(p)
                idx += 1

    # Last-resort Pexels generic anime imagery
    if idx < 5 and pexels_key:
        for q in ['anime art', 'japanese animation', 'manga style', 'tokyo neon']:
            if idx >= target_count:
                break
            for url in _pexels_search(q, pexels_key, count=2):
                if idx >= target_count or url in seen:
                    continue
                seen.add(url)
                p = os.path.join(output_dir, f"img_{idx:03d}.jpg")
                if _download_image(url, p):
                    downloaded.append(p)
                    idx += 1

    print(f"[footage_fetcher] Downloaded {len(downloaded)} anime images")
    return downloaded
