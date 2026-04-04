import os
import requests

PEXELS_API = "https://api.pexels.com/v1"

FALLBACK_QUERIES = [
    "japan city night",
    "anime art fantasy",
    "manga colorful",
    "tokyo street lights",
    "fantasy digital art",
    "sakura cherry blossom",
    "japanese culture",
    "neon lights city",
]

def search_photos(query, api_key, count=3):
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": count,
        "size": "large",
        "orientation": "landscape",
    }
    try:
        r = requests.get(f"{PEXELS_API}/search", headers=headers, params=params, timeout=10)
        r.raise_for_status()
        photos = r.json().get('photos', [])
        return [p['src']['large2x'] for p in photos]
    except Exception as e:
        print(f"[footage_fetcher] Pexels search failed for '{query}': {e}")
        return []

def download_image(url, path):
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

def fetch_footage(news_items, output_dir, api_key, images_per_item=2):
    os.makedirs(output_dir, exist_ok=True)
    downloaded = []

    # Build search queries from news titles
    queries = []
    for item in news_items:
        title_words = item['title'].lower()
        if 'dragon ball' in title_words:
            queries.append('dragon ball fantasy')
        elif 'one piece' in title_words:
            queries.append('ocean adventure anime')
        elif 'naruto' in title_words:
            queries.append('ninja japan')
        elif 'attack on titan' in title_words:
            queries.append('titan fantasy wall')
        elif 'demon slayer' in title_words:
            queries.append('sword fight japan')
        elif 'movie' in title_words or 'film' in title_words:
            queries.append('cinema movie theater')
        elif 'season' in title_words:
            queries.append('japan anime season')
        else:
            queries.append('japan night fantasy')

    # Add fallback queries
    queries += FALLBACK_QUERIES

    image_count = 0
    for query in queries:
        if image_count >= 15:  # Cap at 15 images total
            break
        urls = search_photos(query, api_key, count=images_per_item)
        for url in urls:
            img_path = os.path.join(output_dir, f"img_{image_count:03d}.jpg")
            if download_image(url, img_path):
                downloaded.append(img_path)
                image_count += 1

    print(f"[footage_fetcher] Downloaded {len(downloaded)} images")

    if not downloaded:
        print("[footage_fetcher] No images downloaded — video will use gradient backgrounds")

    return downloaded
