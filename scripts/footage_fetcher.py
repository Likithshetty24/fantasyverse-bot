"""
footage_fetcher.py
Pexels image search for Hindi horror Shorts.
Queries are dark/spooky generic imagery — fog, abandoned places, candles,
old houses, graveyards. All royalty-free.
"""

import os
import requests

PEXELS_API = "https://api.pexels.com/v1"

# Pool of horror-themed search queries — Pexels returns landscape & portrait
# images for these. We pick a varied set per video so backgrounds don't repeat.
HORROR_QUERIES = [
    "dark forest fog",
    "abandoned house night",
    "candle dark room",
    "old hallway dark",
    "haunted window",
    "graveyard mist",
    "creepy doll",
    "broken mirror dark",
    "old indian village night",
    "rural house india night",
    "dark stairs",
    "old well",
    "ghost shadow figure",
    "dark corridor",
    "creepy church night",
    "smoke darkness",
    "moonlight forest",
    "old door creepy",
    "fog road night",
    "abandoned room",
]


def _search_photos(query, api_key, count=2):
    headers = {"Authorization": api_key}
    params = {
        "query":       query,
        "per_page":    count,
        "size":        "large",
        "orientation": "portrait",  # Better for vertical Shorts
    }
    try:
        r = requests.get(f"{PEXELS_API}/search", headers=headers, params=params, timeout=15)
        r.raise_for_status()
        photos = r.json().get('photos', [])
        return [p['src']['large2x'] for p in photos]
    except Exception as e:
        print(f"[footage_fetcher] Pexels failed for '{query}': {e}")
        return []


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


def fetch_footage(output_dir, api_key, target_count=10):
    """
    Download `target_count` dark/spooky portrait images from Pexels.
    Returns list of local image paths.
    """
    os.makedirs(output_dir, exist_ok=True)

    if not api_key:
        print("[footage_fetcher] No PEXELS_API_KEY — video will use gradient backgrounds only")
        return []

    downloaded = []
    seen = set()
    image_count = 0

    for query in HORROR_QUERIES:
        if image_count >= target_count:
            break
        urls = _search_photos(query, api_key, count=2)
        for url in urls:
            if image_count >= target_count:
                break
            if url in seen:
                continue
            seen.add(url)
            img_path = os.path.join(output_dir, f"img_{image_count:03d}.jpg")
            if _download_image(url, img_path):
                downloaded.append(img_path)
                image_count += 1

    print(f"[footage_fetcher] Downloaded {len(downloaded)} horror images")
    return downloaded
