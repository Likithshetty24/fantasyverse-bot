"""
footage_fetcher.py
Pulls imagery that's actually relevant to today's specific story:

  1. Looks up the focus anime on Jikan -> gets its MAL ID
  2. /anime/{id}/pictures   -> 8-15 different key visuals (not just poster)
  3. /characters?q={name}   -> portraits for each mentioned character
  4. Falls back to generic Jikan search + Pexels if targeted fetch fails

This means a Demon Slayer story actually shows multiple Demon Slayer key
visuals + the specific characters mentioned, not the same poster looped.
"""

import os
import re
import time
import requests

JIKAN_SEARCH      = "https://api.jikan.moe/v4/anime"
JIKAN_ANIME       = "https://api.jikan.moe/v4/anime/{id}"
JIKAN_PICTURES    = "https://api.jikan.moe/v4/anime/{id}/pictures"
JIKAN_CHARACTERS  = "https://api.jikan.moe/v4/characters"
JIKAN_TOP         = "https://api.jikan.moe/v4/top/anime"
PEXELS_API        = "https://api.pexels.com/v1"

# Polite delay between Jikan calls (rate limit: ~3/sec)
JIKAN_DELAY = 0.4


# ---------------------------------------------------------------------------
# Jikan: find anime ID by name
# ---------------------------------------------------------------------------

def _find_anime_id(title):
    """Return MAL anime ID for a title, or None."""
    try:
        r = requests.get(
            JIKAN_SEARCH,
            params={'q': title, 'limit': 3, 'order_by': 'popularity'},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json().get('data', [])
        if data:
            anime = data[0]
            print(f"[footage_fetcher] Matched '{title}' -> "
                  f"{anime.get('title')} (ID {anime.get('mal_id')})")
            return anime.get('mal_id')
    except Exception as e:
        print(f"[footage_fetcher] Anime ID lookup failed for '{title}': {e}")
    return None


# ---------------------------------------------------------------------------
# Jikan: multiple pictures for an anime
# ---------------------------------------------------------------------------

def _fetch_anime_pictures(anime_id, max_count=12):
    """Return list of high-res image URLs for one anime."""
    try:
        r = requests.get(JIKAN_PICTURES.format(id=anime_id), timeout=15)
        r.raise_for_status()
        urls = []
        for pic in r.json().get('data', []):
            img = pic.get('jpg', {})
            url = img.get('large_image_url') or img.get('image_url')
            if url:
                urls.append(url)
        urls = urls[:max_count]
        print(f"[footage_fetcher] Got {len(urls)} pictures for anime {anime_id}")
        return urls
    except Exception as e:
        print(f"[footage_fetcher] Pictures fetch failed for anime {anime_id}: {e}")
        return []


# ---------------------------------------------------------------------------
# Jikan: character images
# ---------------------------------------------------------------------------

def _fetch_character_image(name):
    """Return a single character portrait URL for a name."""
    try:
        r = requests.get(
            JIKAN_CHARACTERS,
            params={'q': name, 'limit': 3, 'order_by': 'favorites'},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json().get('data', [])
        if data:
            char = data[0]
            img = char.get('images', {}).get('jpg', {})
            url = img.get('image_url')
            print(f"[footage_fetcher] Character '{name}' -> {char.get('name')}")
            return url
    except Exception as e:
        print(f"[footage_fetcher] Character lookup failed for '{name}': {e}")
    return None


# ---------------------------------------------------------------------------
# Generic fallback (old behaviour)
# ---------------------------------------------------------------------------

FALLBACK_TITLES = [
    'Jujutsu Kaisen', 'Demon Slayer', 'My Hero Academia',
    'One Piece', 'Chainsaw Man', 'Solo Leveling', 'Frieren',
]


def _jikan_search_images(query, limit=5):
    try:
        r = requests.get(
            JIKAN_SEARCH,
            params={'q': query, 'limit': limit, 'order_by': 'score', 'sort': 'desc'},
            timeout=15,
        )
        r.raise_for_status()
        urls = []
        for entry in r.json().get('data', []):
            url = entry.get('images', {}).get('jpg', {}).get('large_image_url')
            if url:
                urls.append(url)
        return urls
    except Exception:
        return []


def _pexels_search(query, api_key, count=2):
    if not api_key:
        return []
    try:
        r = requests.get(
            f"{PEXELS_API}/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": count, "orientation": "portrait"},
            timeout=15,
        )
        r.raise_for_status()
        return [p['src']['large2x'] for p in r.json().get('photos', [])]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------

def _download(url, path):
    try:
        r = requests.get(url, timeout=20, stream=True)
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"[footage_fetcher] Download failed {url[:60]}: {e}")
        return False


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def fetch_footage(focus_anime, focus_characters, output_dir,
                  pexels_key=None, target_count=12):
    """
    Targeted fetch for today's story.

    Args:
        focus_anime:      str - primary anime from script_generator (e.g., "Demon Slayer")
        focus_characters: list[str] - mentioned character names
        output_dir:       where to save downloaded jpgs
        pexels_key:       optional Pexels key for last-resort fallback
        target_count:     how many images to end up with

    Returns:
        list of local image paths
    """
    os.makedirs(output_dir, exist_ok=True)
    downloaded = []
    seen = set()
    idx = 0

    # ---- 1. Anime-specific multi-image pull ----
    if focus_anime:
        anime_id = _find_anime_id(focus_anime)
        time.sleep(JIKAN_DELAY)

        if anime_id:
            for url in _fetch_anime_pictures(anime_id, max_count=10):
                if idx >= target_count or url in seen:
                    continue
                seen.add(url)
                p = os.path.join(output_dir, f"img_{idx:03d}_anime.jpg")
                if _download(url, p):
                    downloaded.append(p)
                    idx += 1
            time.sleep(JIKAN_DELAY)

    # ---- 2. Character portraits ----
    for char_name in (focus_characters or []):
        if idx >= target_count:
            break
        url = _fetch_character_image(char_name)
        time.sleep(JIKAN_DELAY)
        if url and url not in seen:
            seen.add(url)
            p = os.path.join(output_dir, f"img_{idx:03d}_char.jpg")
            if _download(url, p):
                downloaded.append(p)
                idx += 1

    # ---- 3. If we're short, top up with related anime ----
    if idx < 6 and focus_anime:
        for url in _jikan_search_images(focus_anime, limit=5):
            if idx >= target_count or url in seen:
                continue
            seen.add(url)
            p = os.path.join(output_dir, f"img_{idx:03d}_related.jpg")
            if _download(url, p):
                downloaded.append(p)
                idx += 1
        time.sleep(JIKAN_DELAY)

    # ---- 4. Last resort: popular anime ----
    if idx < 5:
        print("[footage_fetcher] Topping up with fallback titles...")
        for fallback in FALLBACK_TITLES:
            if idx >= target_count:
                break
            for url in _jikan_search_images(fallback, limit=2):
                if idx >= target_count or url in seen:
                    continue
                seen.add(url)
                p = os.path.join(output_dir, f"img_{idx:03d}_fallback.jpg")
                if _download(url, p):
                    downloaded.append(p)
                    idx += 1
            time.sleep(JIKAN_DELAY)

    # ---- 5. Absolute fallback: Pexels ----
    if idx < 3 and pexels_key:
        for q in ['anime art', 'japanese animation', 'manga style']:
            if idx >= target_count:
                break
            for url in _pexels_search(q, pexels_key, count=2):
                if idx >= target_count or url in seen:
                    continue
                seen.add(url)
                p = os.path.join(output_dir, f"img_{idx:03d}_pexels.jpg")
                if _download(url, p):
                    downloaded.append(p)
                    idx += 1

    print(f"[footage_fetcher] Downloaded {len(downloaded)} images "
          f"(anime-specific: {sum(1 for p in downloaded if 'anime' in p or 'char' in p)})")
    return downloaded
