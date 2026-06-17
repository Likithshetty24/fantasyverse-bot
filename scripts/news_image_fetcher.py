"""
news_image_fetcher.py — Extra Time
Fetches CURRENT, on-topic images for the specific story/match being covered:

  - og:image meta tag from the news article we're reacting to (BBC/Guardian/
    Reddit) — usually a current photo of that match/player
  - Reddit r/soccer search for a match (team names) -> current post images

These are press/agency photos used under fair-use commentary. They are
always run through the heavy blur + grade + vignette in prepare_background,
so they appear as stylized (transformative) backgrounds, not verbatim.

Best-effort: returns [] on any failure (callers fall back to stock).
"""

import os
import re
import html
import requests

UA = {'User-Agent': 'ExtraTimeBot/1.0 (football shorts)'}
MIN_FILESIZE = 6000

_OG_A = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I)
_OG_B = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.I)


def _download(url, path):
    try:
        url = html.unescape(url)
        r = requests.get(url, timeout=20, stream=True, headers=UA)
        r.raise_for_status()
        if 'image' not in r.headers.get('Content-Type', ''):
            return False
        with open(path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        if os.path.getsize(path) < MIN_FILESIZE:
            os.remove(path)
            return False
        return True
    except Exception as e:
        print(f"[news_img] download failed {url[:60]}: {e}")
        if os.path.exists(path):
            try: os.remove(path)
            except: pass
        return False


def _og_image(page_url):
    try:
        r = requests.get(page_url, timeout=15, headers=UA)
        r.raise_for_status()
        m = _OG_A.search(r.text) or _OG_B.search(r.text)
        return html.unescape(m.group(1)) if m else None
    except Exception as e:
        print(f"[news_img] og:image fetch failed: {e}")
        return None


def fetch_current_images(news_item, output_dir, max_n=3):
    """Current images for a news story we're reacting to."""
    os.makedirs(output_dir, exist_ok=True)
    candidates = []
    if news_item.get('image_url'):
        candidates.append(news_item['image_url'])
    if news_item.get('link'):
        og = _og_image(news_item['link'])
        if og:
            candidates.append(og)

    paths, seen, idx = [], set(), 0
    for u in candidates:
        if idx >= max_n or u in seen:
            continue
        seen.add(u)
        p = os.path.join(output_dir, f"live_{idx:02d}.jpg")
        if _download(u, p):
            paths.append(p)
            idx += 1
    print(f"[news_img] {len(paths)} current article image(s)")
    return paths


def search_match_images(home, away, output_dir, max_n=3):
    """Current images for a specific match via Reddit r/soccer search."""
    os.makedirs(output_dir, exist_ok=True)
    paths, seen, idx = [], set(), 0
    try:
        r = requests.get(
            "https://www.reddit.com/r/soccer/search.json",
            params={'q': f"{home} {away}", 'restrict_sr': 1,
                    'sort': 'new', 't': 'week', 'limit': 12},
            headers=UA, timeout=15,
        )
        r.raise_for_status()
        for ch in r.json().get('data', {}).get('children', []):
            if idx >= max_n:
                break
            d = ch.get('data', {}) or {}
            url = None
            prev = d.get('preview', {})
            if isinstance(prev, dict) and prev.get('images'):
                url = (prev['images'][0].get('source', {}) or {}).get('url')
            if not url and d.get('url', '').lower().endswith(('.jpg', '.jpeg', '.png')):
                url = d['url']
            if not url or url in seen:
                continue
            seen.add(url)
            p = os.path.join(output_dir, f"live_{idx:02d}.jpg")
            if _download(url, p):
                paths.append(p)
                idx += 1
    except Exception as e:
        print(f"[news_img] match image search failed: {e}")
    print(f"[news_img] {len(paths)} current match image(s) for {home} vs {away}")
    return paths
