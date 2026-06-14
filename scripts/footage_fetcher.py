"""
footage_fetcher.py — Extra Time (football imagery)

Sources (all free):
  1. TheSportsDB   — real player photos, team badges, stadium fanart (free key '3')
  2. Pollinations  — AI-generated football stadium/action aesthetic
  3. Pexels        — football stock (crowds, stadiums, pitch) [needs key]
  4. Unsplash      — football-keyword fallback (no key)
"""

import os
import time
import urllib.parse
import requests

THESPORTSDB   = "https://www.thesportsdb.com/api/v1/json/3"
POLLINATIONS  = "https://image.pollinations.ai/prompt/{prompt}"
PEXELS_API    = "https://api.pexels.com/v1"
UNSPLASH_SRC  = "https://source.unsplash.com"

DEFAULT_TIMEOUT = 45
MIN_FILESIZE    = 6000

STYLE_TOKENS = (
    "cinematic, dramatic stadium lighting, vertical 9:16, 4k, "
    "football atmosphere, vibrant, high energy, no text, no logos"
)

PROMPT_VARIANTS = [
    "packed stadium under floodlights",
    "football on the pitch close-up",
    "roaring crowd with flags",
    "player silhouette celebrating",
    "stadium tunnel dramatic",
    "green pitch aerial view",
    "trophy gleaming in spotlight",
    "fireworks over a stadium",
]

PEXELS_FALLBACK = [
    "football stadium night", "soccer crowd", "football pitch",
    "soccer ball grass", "stadium floodlights", "football fans flags",
    "soccer celebration", "world cup atmosphere",
]

UNSPLASH_KEYWORDS = ['football-stadium', 'soccer', 'football-pitch',
                     'stadium-crowd', 'soccer-ball', 'football-fans']


def _download(url, path, timeout=DEFAULT_TIMEOUT):
    try:
        r = requests.get(url, timeout=timeout, stream=True, allow_redirects=True,
                         headers={'User-Agent': 'ExtraTimeBot/1.0'})
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        if os.path.getsize(path) < MIN_FILESIZE:
            os.remove(path)
            return False
        return True
    except Exception as e:
        print(f"[footage] Download failed {url[:70]}: {e}")
        if os.path.exists(path):
            try: os.remove(path)
            except: pass
        return False


# ---------------------------------------------------------------------------
# 1. TheSportsDB — real player / team imagery
# ---------------------------------------------------------------------------

def _sportsdb_player_images(name):
    """Return player photo URLs (thumb, cutout, render)."""
    try:
        r = requests.get(f"{THESPORTSDB}/searchplayers.php",
                         params={'p': name}, timeout=15)
        r.raise_for_status()
        players = r.json().get('player') or []
        if not players:
            return []
        p = players[0]
        urls = []
        for key in ('strThumb', 'strCutout', 'strRender', 'strFanart1',
                    'strFanart2', 'strFanart3', 'strFanart4'):
            u = p.get(key)
            if u:
                urls.append(u)
        print(f"[footage] TheSportsDB player '{name}': {len(urls)} images")
        return urls
    except Exception as e:
        print(f"[footage] TheSportsDB player lookup failed for '{name}': {e}")
        return []


def _sportsdb_team_images(name):
    """Return team fanart / stadium / badge URLs."""
    try:
        r = requests.get(f"{THESPORTSDB}/searchteams.php",
                         params={'t': name}, timeout=15)
        r.raise_for_status()
        teams = r.json().get('teams') or []
        if not teams:
            return []
        t = teams[0]
        urls = []
        for key in ('strFanart1', 'strFanart2', 'strFanart3', 'strFanart4',
                    'strStadiumThumb', 'strBadge'):
            u = t.get(key)
            if u:
                urls.append(u)
        print(f"[footage] TheSportsDB team '{name}': {len(urls)} images")
        return urls
    except Exception as e:
        print(f"[footage] TheSportsDB team lookup failed for '{name}': {e}")
        return []


# ---------------------------------------------------------------------------
# 2. Pollinations
# ---------------------------------------------------------------------------

def _pollinations_url(prompt, seed=None):
    encoded = urllib.parse.quote(prompt, safe='')
    url = (f"{POLLINATIONS.format(prompt=encoded)}"
           f"?width=1080&height=1920&model=flux&nologo=true&enhance=true")
    if seed is not None:
        url += f"&seed={seed}"
    return url


def _build_prompts(subject, count=6):
    base = f"{subject} football" if subject else "world cup football"
    prompts = []
    for i in range(count):
        variant = PROMPT_VARIANTS[i % len(PROMPT_VARIANTS)]
        prompts.append(f"{base}, {variant}, {STYLE_TOKENS}")
    return prompts


# ---------------------------------------------------------------------------
# 3. Pexels
# ---------------------------------------------------------------------------

def _pexels_search(query, api_key, count=2):
    if not api_key:
        return []
    try:
        r = requests.get(f"{PEXELS_API}/search",
                         headers={"Authorization": api_key},
                         params={"query": query, "per_page": count,
                                 "orientation": "portrait", "size": "large"},
                         timeout=15)
        r.raise_for_status()
        return [p['src']['large2x'] for p in r.json().get('photos', [])]
    except Exception as e:
        print(f"[footage] Pexels failed for '{query}': {e}")
        return []


def _unsplash_url(keyword, seed=0):
    return f"{UNSPLASH_SRC}/1080x1920/?{keyword}&sig={seed}"


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def fetch_footage(image_subject, output_dir, pexels_key=None,
                  target_count=10, rng_seed=None):
    """
    image_subject: a player name, team name, or '' for generic football.
    Returns list of local image paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    downloaded = []
    seen = set()
    idx = 0

    def save(url, tag, timeout=DEFAULT_TIMEOUT):
        nonlocal idx
        if not url or url in seen or idx >= target_count:
            return False
        seen.add(url)
        p = os.path.join(output_dir, f"img_{idx:03d}_{tag}.jpg")
        if _download(url, p, timeout=timeout):
            downloaded.append(p)
            idx += 1
            return True
        return False

    TEAMS = {'argentina', 'france', 'brazil', 'england', 'spain', 'germany',
             'portugal', 'netherlands', 'italy', 'croatia'}

    # ---- 1. Real imagery for a named subject ----
    if image_subject:
        if image_subject.lower() in TEAMS:
            for url in _sportsdb_team_images(image_subject):
                save(url, 'team', timeout=20)
        else:
            for url in _sportsdb_player_images(image_subject):
                save(url, 'player', timeout=20)
        time.sleep(0.3)

    # ---- 2. Pollinations football scenes ----
    base_seed = abs(hash(rng_seed or '')) % (2**31) if rng_seed else None
    for i, prompt in enumerate(_build_prompts(image_subject, count=target_count)):
        if idx >= target_count:
            break
        seed = (base_seed + i) % (2**31) if base_seed is not None else None
        save(_pollinations_url(prompt, seed=seed), 'ai')

    # ---- 3. Pexels fallback ----
    if idx < target_count and pexels_key:
        print("[footage] Topping up with Pexels...")
        for q in PEXELS_FALLBACK:
            if idx >= target_count:
                break
            for url in _pexels_search(q, pexels_key, count=2):
                save(url, 'pex', timeout=20)

    # ---- 4. Unsplash last resort ----
    if idx < target_count:
        print("[footage] Topping up with Unsplash...")
        for kw in UNSPLASH_KEYWORDS:
            if idx >= target_count:
                break
            save(_unsplash_url(kw, seed=(base_seed or 1) + idx), 'us', timeout=20)

    print(f"[footage] Total downloaded: {len(downloaded)} images (target: {target_count})")
    return downloaded
