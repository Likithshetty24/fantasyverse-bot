import os
import re
import time
import requests

# ---------------------------------------------------------------------------
# Jikan API  (MyAnimeList data — free, no API key)
# ---------------------------------------------------------------------------

JIKAN_SEARCH = "https://api.jikan.moe/v4/anime"
JIKAN_TOP    = "https://api.jikan.moe/v4/top/anime"

# Generic fallback search terms mapped from common news keywords
KEYWORD_MAP = {
    'dragon ball':    ['Dragon Ball', 'Dragon Ball Super'],
    'one piece':      ['One Piece'],
    'naruto':         ['Naruto', 'Boruto'],
    'attack on titan':['Attack on Titan'],
    'demon slayer':   ['Demon Slayer', 'Kimetsu no Yaiba'],
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
}

FALLBACK_TITLES = [
    'Jujutsu Kaisen',
    'Demon Slayer',
    'My Hero Academia',
    'One Piece',
    'Attack on Titan',
    'Chainsaw Man',
    'Spy x Family',
    'Dragon Ball Super',
]


def _jikan_search(query, retries=3):
    """Return list of image URLs from Jikan for a given anime title query."""
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
            data = r.json().get('data', [])
            urls = []
            for entry in data:
                img = entry.get('images', {})
                large = img.get('jpg', {}).get('large_image_url')
                if large:
                    urls.append(large)
            return urls
        except Exception as e:
            print(f"[footage_fetcher] Jikan search failed for '{query}': {e}")
            time.sleep(1)
    return []


def _jikan_top(limit=10):
    """Return top anime image URLs from Jikan."""
    try:
        r = requests.get(JIKAN_TOP, params={'limit': limit}, timeout=15)
        r.raise_for_status()
        data = r.json().get('data', [])
        urls = []
        for entry in data:
            img  = entry.get('images', {})
            large = img.get('jpg', {}).get('large_image_url')
            if large:
                urls.append(large)
        return urls
    except Exception as e:
        print(f"[footage_fetcher] Jikan top failed: {e}")
        return []


def _extract_anime_titles(news_items):
    """Map news item titles to specific anime series names for targeted search."""
    queries = []
    for item in news_items:
        lower = item['title'].lower() + ' ' + item.get('summary', '').lower()
        matched = False
        for keyword, titles in KEYWORD_MAP.items():
            if keyword in lower:
                queries.extend(titles)
                matched = True
                break
        if not matched:
            # Try to extract a capitalised phrase as anime name
            # e.g.  "Blue Lock Season 3 announced" -> "Blue Lock"
            cap_match = re.search(r'\b([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)+)\b', item['title'])
            if cap_match:
                queries.append(cap_match.group(1))
            else:
                queries.append('anime')
    return queries


def _download_image(url, path):
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


def fetch_footage(news_items, output_dir, _api_key=None, images_per_item=3):
    """
    Fetch real anime artwork from Jikan (MyAnimeList).
    _api_key is accepted but ignored — Jikan is free.
    """
    os.makedirs(output_dir, exist_ok=True)
    downloaded = []

    queries = _extract_anime_titles(news_items)
    # Add fallback titles so we always have enough images
    queries += FALLBACK_TITLES

    seen_urls = set()
    image_count = 0

    for query in queries:
        if image_count >= 15:
            break
        urls = _jikan_search(query)
        # Jikan rate-limit: 3 requests/sec
        time.sleep(0.4)

        for url in urls:
            if image_count >= 15:
                break
            if url in seen_urls:
                continue
            seen_urls.add(url)
            img_path = os.path.join(output_dir, f"img_{image_count:03d}.jpg")
            if _download_image(url, img_path):
                downloaded.append(img_path)
                image_count += 1

    # If still short, grab top anime art
    if image_count < 5:
        print("[footage_fetcher] Supplementing with Jikan top anime...")
        for url in _jikan_top(20):
            if image_count >= 15:
                break
            if url in seen_urls:
                continue
            seen_urls.add(url)
            img_path = os.path.join(output_dir, f"img_{image_count:03d}.jpg")
            if _download_image(url, img_path):
                downloaded.append(img_path)
                image_count += 1

    print(f"[footage_fetcher] Downloaded {len(downloaded)} anime images")
    if not downloaded:
        print("[footage_fetcher] No images — video will use gradient backgrounds")
    return downloaded
