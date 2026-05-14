"""
footage_fetcher.py
Cinematic mindset/wealth-aesthetic imagery for Daulat Mantra.

Primary source: Pollinations.ai (free AI image generation, no key)
  - Generates exactly the prompt we want, every time
  - Vertical 1080x1920 native
  - Each topic in topic_picker.py ships with its own image_prompt seed

Secondary: Pexels (mindset/wealth/nature stock photos)
  - Fallback if Pollinations is slow or returns broken images
"""

import os
import time
import urllib.parse
import requests


POLLINATIONS = "https://image.pollinations.ai/prompt/{prompt}"
PEXELS_API   = "https://api.pexels.com/v1"

DEFAULT_TIMEOUT = 45  # Pollinations can take 10-30 sec per image
MIN_FILESIZE    = 6000


# Universal cinematic style tokens added to every Pollinations prompt
STYLE_TOKENS = (
    "cinematic, dramatic lighting, vertical 9:16 composition, 4k, atmospheric, "
    "moody, photographic, high contrast, no text"
)


# Generic prompt variations that we add to each seed prompt for variety
PROMPT_VARIANTS = [
    "ultra wide shot",
    "close-up detail shot",
    "silhouette against light",
    "golden hour lighting",
    "blue hour mood",
    "shallow depth of field",
    "low angle dramatic",
    "overhead perspective",
]


# Pexels fallback queries for mindset/wealth aesthetic
PEXELS_FALLBACK_QUERIES = [
    "mountain sunrise silhouette",
    "alone walking sunset",
    "ancient temple",
    "gold coins dark",
    "meditation peaceful",
    "candle dark wood",
    "old book vintage",
    "fog mountain peak",
    "luxury watch dark",
    "ocean horizon dawn",
]


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------

def _download(url, path, timeout=DEFAULT_TIMEOUT):
    try:
        r = requests.get(
            url, timeout=timeout, stream=True,
            headers={'User-Agent': 'DaulatMantraBot/1.0'},
        )
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
# 1. Pollinations.ai — AI image generation
# ---------------------------------------------------------------------------

def _pollinations_url(prompt, seed=None):
    encoded = urllib.parse.quote(prompt, safe='')
    url = (f"{POLLINATIONS.format(prompt=encoded)}"
           f"?width=1080&height=1920&model=flux&nologo=true&enhance=true")
    if seed is not None:
        url += f"&seed={seed}"
    return url


def _build_prompts(base_prompt, count=8):
    """Generate `count` varied prompts based on the seed image prompt."""
    prompts = []
    for i in range(count):
        variant = PROMPT_VARIANTS[i % len(PROMPT_VARIANTS)]
        prompt = f"{base_prompt}, {variant}, {STYLE_TOKENS}"
        prompts.append(prompt)
    return prompts


# ---------------------------------------------------------------------------
# 2. Pexels — fallback / supplementation
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
# Public
# ---------------------------------------------------------------------------

def fetch_footage(image_prompt, output_dir, pexels_key=None,
                  target_count=10, rng_seed=None):
    """
    Args:
        image_prompt: base prompt from topic_picker
        output_dir:   where to save .jpg files
        pexels_key:   optional Pexels key for fallback
        target_count: how many images to return
        rng_seed:     string seed (e.g. 'YYYYMMDD') for Pollinations seed param
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

    # ---- Primary: Pollinations (AI-generated, exact-match) ----
    base_seed = abs(hash(rng_seed or '')) % (2**31) if rng_seed else None
    prompts = _build_prompts(image_prompt, count=target_count)
    print(f"[footage] Generating {len(prompts)} Pollinations images...")

    for i, prompt in enumerate(prompts):
        if idx >= target_count:
            break
        seed = (base_seed + i) % (2**31) if base_seed is not None else None
        url = _pollinations_url(prompt, seed=seed)
        save(url, 'ai')

    # ---- Fallback: Pexels if we got fewer than expected ----
    if idx < target_count and pexels_key:
        print(f"[footage] Only {idx} from Pollinations — topping up with Pexels...")
        for q in PEXELS_FALLBACK_QUERIES:
            if idx >= target_count:
                break
            for url in _pexels_search(q, pexels_key, count=2):
                save(url, 'pex', timeout=20)

    print(f"[footage] Total downloaded: {len(downloaded)} images (target: {target_count})")
    return downloaded
