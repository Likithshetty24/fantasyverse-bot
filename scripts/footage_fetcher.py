"""
footage_fetcher.py
Pulls high-quality imagery from MULTIPLE free sources and mixes them:

  1. Wallhaven       - 4K anime wallpapers (no API key)
  2. Safebooru       - Tag-indexed anime art, huge variety (no API key)
  3. Jikan/MAL       - Official character portraits & key visuals (no API key)
  4. Pollinations.ai - AI-generated scene-specific images (no API key)

All sources are free, no keys, SFW filters applied.
"""

import os
import re
import time
import urllib.parse
import requests

# ---- Source endpoints -------------------------------------------------------
WALLHAVEN_API    = "https://wallhaven.cc/api/v1/search"
SAFEBOORU_API    = "https://safebooru.org/index.php"
JIKAN_SEARCH     = "https://api.jikan.moe/v4/anime"
JIKAN_PICTURES   = "https://api.jikan.moe/v4/anime/{id}/pictures"
JIKAN_CHARACTERS = "https://api.jikan.moe/v4/characters"
POLLINATIONS     = "https://image.pollinations.ai/prompt/{prompt}"

JIKAN_DELAY      = 0.4
DEFAULT_TIMEOUT  = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safebooru_tag(name):
    """Convert 'Demon Slayer' → 'demon_slayer' (Safebooru tag format)."""
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def _download(url, path):
    try:
        r = requests.get(url, timeout=DEFAULT_TIMEOUT, stream=True,
                         headers={'User-Agent': 'FantasyVerseBot/1.0'})
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        # Sanity-check the file size
        if os.path.getsize(path) < 4000:
            os.remove(path)
            return False
        return True
    except Exception as e:
        print(f"[footage] Download failed {url[:70]}: {e}")
        return False


# ---------------------------------------------------------------------------
# 1. Wallhaven — high-res anime wallpapers
# ---------------------------------------------------------------------------

def _wallhaven_search(query, limit=6):
    """Returns list of high-res wallpaper URLs."""
    try:
        params = {
            'q':         query,
            'categories':'010',     # anime only
            'purity':    '100',     # SFW only
            'sorting':   'relevance',
            'ratios':    'portrait,9x16,9x18',
            'atleast':   '1080x1920',
        }
        r = requests.get(WALLHAVEN_API, params=params, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        data = r.json().get('data', [])
        urls = [w['path'] for w in data[:limit] if w.get('path')]
        print(f"[footage] Wallhaven '{query}': {len(urls)} hits")
        return urls
    except Exception as e:
        print(f"[footage] Wallhaven failed for '{query}': {e}")
        return []


# ---------------------------------------------------------------------------
# 2. Safebooru — tag-indexed anime art
# ---------------------------------------------------------------------------

def _safebooru_search(tag, limit=8):
    """Returns list of art URLs filtered by tag (e.g. 'demon_slayer')."""
    try:
        params = {
            'page':  'dapi',
            's':     'post',
            'q':     'index',
            'json':  '1',
            'tags':  f"{tag} rating:safe",
            'limit': limit,
        }
        r = requests.get(SAFEBOORU_API, params=params, timeout=DEFAULT_TIMEOUT,
                         headers={'User-Agent': 'FantasyVerseBot/1.0'})
        r.raise_for_status()
        posts = r.json() or []
        urls = []
        for p in posts:
            # Safebooru sometimes nests, sometimes flat
            url = p.get('file_url') or p.get('sample_url')
            if not url and p.get('directory') and p.get('image'):
                url = f"https://safebooru.org//images/{p['directory']}/{p['image']}"
            if url:
                urls.append(url)
        print(f"[footage] Safebooru '{tag}': {len(urls)} hits")
        return urls
    except Exception as e:
        print(f"[footage] Safebooru failed for '{tag}': {e}")
        return []


# ---------------------------------------------------------------------------
# 3. Jikan — official poster/character art
# ---------------------------------------------------------------------------

def jikan_anime_id(title):
    """Public alias — main.py uses this to resolve anime ID once."""
    return _jikan_anime_id(title)


def _jikan_anime_id(title):
    try:
        r = requests.get(JIKAN_SEARCH,
                         params={'q': title, 'limit': 3, 'order_by': 'popularity'},
                         timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        data = r.json().get('data', [])
        if data:
            return data[0].get('mal_id')
    except Exception as e:
        print(f"[footage] Jikan ID lookup failed for '{title}': {e}")
    return None


def _jikan_pictures(anime_id, limit=6):
    try:
        r = requests.get(JIKAN_PICTURES.format(id=anime_id), timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        urls = []
        for pic in r.json().get('data', []):
            img = pic.get('jpg', {})
            u = img.get('large_image_url') or img.get('image_url')
            if u:
                urls.append(u)
        return urls[:limit]
    except Exception:
        return []


def _jikan_character(name):
    try:
        r = requests.get(JIKAN_CHARACTERS,
                         params={'q': name, 'limit': 3, 'order_by': 'favorites'},
                         timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        data = r.json().get('data', [])
        if data:
            return data[0].get('images', {}).get('jpg', {}).get('image_url')
    except Exception:
        return None
    return None


# ---------------------------------------------------------------------------
# 4. Pollinations.ai — AI-generated scene images
# ---------------------------------------------------------------------------

def _pollinations_url(prompt):
    """Build a direct image URL — Pollinations generates on GET."""
    encoded = urllib.parse.quote(prompt, safe='')
    return (
        f"{POLLINATIONS.format(prompt=encoded)}"
        f"?width=1080&height=1920&model=flux&nologo=true&enhance=true"
    )


def _pollinations_prompts(anime, characters):
    """Build 2-3 cinematic prompts for the AI generator."""
    base_style = "anime style, cinematic, dramatic lighting, vertical composition, 4k, vibrant colors"
    prompts = [f"epic scene from {anime}, dynamic pose, {base_style}"]

    if characters:
        char = characters[0]
        prompts.append(f"{char} from {anime}, close-up portrait, intense expression, {base_style}")

    prompts.append(f"{anime} aesthetic background, atmospheric, no characters, {base_style}")
    return prompts


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def fetch_footage(focus_anime, focus_characters, output_dir,
                  pexels_key=None, target_count=15):
    """
    Pull a varied mix of high-quality imagery for today's anime.
    Returns list of local image paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    downloaded = []
    seen = set()
    idx = 0

    def save(url, source_tag):
        nonlocal idx
        if not url or url in seen or idx >= target_count:
            return False
        seen.add(url)
        p = os.path.join(output_dir, f"img_{idx:03d}_{source_tag}.jpg")
        if _download(url, p):
            downloaded.append(p)
            idx += 1
            return True
        return False

    # ---- 1. Wallhaven (4K anime wallpapers) ----
    for url in _wallhaven_search(focus_anime, limit=5):
        save(url, 'wh')

    # ---- 2. Safebooru (tagged anime art) ----
    sb_tag = _safebooru_tag(focus_anime)
    for url in _safebooru_search(sb_tag, limit=6):
        save(url, 'sb')

    # ---- 3. Jikan (official posters + character portraits) ----
    anime_id = _jikan_anime_id(focus_anime)
    time.sleep(JIKAN_DELAY)
    if anime_id:
        for url in _jikan_pictures(anime_id, limit=4):
            save(url, 'mal')
        time.sleep(JIKAN_DELAY)

    for char in (focus_characters or [])[:4]:
        if idx >= target_count:
            break
        char_url = _jikan_character(char)
        time.sleep(JIKAN_DELAY)
        if char_url:
            save(char_url, 'char')

    # ---- 4. Pollinations AI-generated scenes ----
    # Only fire 2 generations to avoid long waits (each takes 5-15 sec)
    if idx < target_count - 1:
        prompts = _pollinations_prompts(focus_anime, focus_characters)
        for prompt in prompts[:2]:
            if idx >= target_count:
                break
            url = _pollinations_url(prompt)
            save(url, 'ai')

    # ---- Last resort: searching Wallhaven by character if low count ----
    if idx < 5 and focus_characters:
        for char in focus_characters[:2]:
            for url in _wallhaven_search(char, limit=3):
                save(url, 'wh-char')

    print(f"[footage] Total downloaded: {len(downloaded)} images "
          f"(targets: {target_count})")
    return downloaded
