"""
footage_fetcher.py — The AI Stack
Tech / AI / cyber-aesthetic imagery for educational Shorts.

Sources (all free, no keys except optional Pexels):
  1. Pollinations.ai — AI-generated tech visuals matched to the topic
  2. Pexels         — high-quality tech/coding stock (needs key)
  3. Unsplash       — fallback CDN endpoint (no key, no API)
"""

import os
import time
import urllib.parse
import requests

POLLINATIONS  = "https://image.pollinations.ai/prompt/{prompt}"
PEXELS_API    = "https://api.pexels.com/v1"
UNSPLASH_SRC  = "https://source.unsplash.com"  # no auth, redirects to random image

DEFAULT_TIMEOUT = 45
MIN_FILESIZE    = 6000


# Tech-aesthetic style tokens added to every Pollinations prompt
STYLE_TOKENS = (
    "cinematic, dramatic lighting, vertical 9:16, 4k, "
    "futuristic technology aesthetic, neon cyan and blue accents, "
    "dark background, glowing details, no text, no logos"
)


PROMPT_VARIANTS = [
    "wide cinematic shot",
    "close-up macro detail",
    "abstract data visualization",
    "neural network flowing particles",
    "holographic UI floating",
    "code on glowing screen",
    "circuit board macro",
    "developer workspace at night",
    "AI brain abstract",
    "digital flow lines",
]


# Pexels fallback queries for tech/AI aesthetic
PEXELS_FALLBACK_QUERIES = [
    "coding screen dark",
    "neural network abstract",
    "ai abstract technology",
    "cyberpunk neon city",
    "data visualization blue",
    "futuristic technology",
    "circuit board macro",
    "developer workspace dark",
    "robot artificial intelligence",
    "holographic display",
    "matrix code",
    "server data center",
]


# Unsplash topic keywords for the no-key fallback
UNSPLASH_KEYWORDS = ['technology', 'coding', 'ai', 'cyber', 'matrix',
                     'neural-network', 'tech', 'futuristic', 'data', 'circuit']


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------

def _download(url, path, timeout=DEFAULT_TIMEOUT):
    try:
        r = requests.get(url, timeout=timeout, stream=True, allow_redirects=True,
                         headers={'User-Agent': 'TheAIStackBot/1.0'})
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        if os.path.getsize(path) < MIN_FILESIZE:
            os.remove(path)
            return False
        return True
    except Exception as e:
        print(f"[footage] Download failed {url[:80]}: {e}")
        if os.path.exists(path):
            try: os.remove(path)
            except: pass
        return False


# ---------------------------------------------------------------------------
# Pollinations (primary)
# ---------------------------------------------------------------------------

def _pollinations_url(prompt, seed=None):
    encoded = urllib.parse.quote(prompt, safe='')
    url = (f"{POLLINATIONS.format(prompt=encoded)}"
           f"?width=1080&height=1920&model=flux&nologo=true&enhance=true")
    if seed is not None:
        url += f"&seed={seed}"
    return url


def _build_pollinations_prompts(topic_title, count=8):
    """Build varied cinematic prompts for the day's topic."""
    base = f"abstract visualization of {topic_title}"
    prompts = []
    for i in range(count):
        variant = PROMPT_VARIANTS[i % len(PROMPT_VARIANTS)]
        prompts.append(f"{base}, {variant}, {STYLE_TOKENS}")
    return prompts


# ---------------------------------------------------------------------------
# Pexels
# ---------------------------------------------------------------------------

def _pexels_search(query, api_key, count=2):
    if not api_key:
        return []
    try:
        r = requests.get(
            f"{PEXELS_API}/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": count,
                    "orientation": "portrait", "size": "large"},
            timeout=15,
        )
        r.raise_for_status()
        return [p['src']['large2x'] for p in r.json().get('photos', [])]
    except Exception as e:
        print(f"[footage] Pexels failed for '{query}': {e}")
        return []


# ---------------------------------------------------------------------------
# Unsplash (no key — public source endpoint)
# ---------------------------------------------------------------------------

def _unsplash_url(keyword, seed=0):
    # source.unsplash.com redirects to a random photo matching the keyword
    return f"{UNSPLASH_SRC}/1080x1920/?{keyword}&sig={seed}"


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def fetch_footage(topic_title, output_dir, pexels_key=None,
                  target_count=10, rng_seed=None):
    """
    Pull tech/AI-aesthetic imagery matched to today's topic.
    Returns list of local image paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    downloaded = []
    idx = 0

    def save(url, source_tag, timeout=DEFAULT_TIMEOUT):
        nonlocal idx
        if idx >= target_count:
            return False
        p = os.path.join(output_dir, f"img_{idx:03d}_{source_tag}.jpg")
        if _download(url, p, timeout=timeout):
            downloaded.append(p)
            idx += 1
            return True
        return False

    # ---- 1. Pollinations (AI-generated, topic-matched) ----
    base_seed = abs(hash(rng_seed or '')) % (2**31) if rng_seed else None
    prompts = _build_pollinations_prompts(topic_title, count=target_count)
    print(f"[footage] Generating up to {len(prompts)} Pollinations images...")
    for i, prompt in enumerate(prompts):
        if idx >= target_count:
            break
        seed = (base_seed + i) % (2**31) if base_seed is not None else None
        save(_pollinations_url(prompt, seed=seed), 'ai')

    # ---- 2. Pexels fallback ----
    if idx < target_count and pexels_key:
        print(f"[footage] Topping up with Pexels...")
        for q in PEXELS_FALLBACK_QUERIES:
            if idx >= target_count:
                break
            for url in _pexels_search(q, pexels_key, count=2):
                save(url, 'pex', timeout=20)

    # ---- 3. Unsplash last-resort ----
    if idx < target_count:
        print(f"[footage] Topping up with Unsplash...")
        seed = (base_seed or 1) + idx
        for kw in UNSPLASH_KEYWORDS:
            if idx >= target_count:
                break
            save(_unsplash_url(kw, seed=seed + idx), 'us', timeout=20)

    print(f"[footage] Total downloaded: {len(downloaded)} images (target: {target_count})")
    return downloaded
