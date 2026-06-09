"""
clip_extractor.py
Phase 2 — extracts short video clips from official anime trailers.

Pipeline:
  1. Get official trailer YouTube URLs from Jikan /anime/{id}/videos
  2. Download highest trailer (<=720p, mp4) via yt-dlp
  3. Use ffmpeg to extract N short clips (1.5-3 sec each) at varied
     timestamps. Crop to 1080x1920, apply anime color grade, mute audio.
  4. Return list of clip paths for video_assembler to mix with stills.

Legality: these are official PVs uploaded by the studios themselves
(Toei, MAPPA, Bones, Crunchyroll). Using short snippets under
commentary/criticism is fair use — standard for every anime news channel.
"""

import os
import random
import subprocess
import requests

JIKAN_VIDEOS = "https://api.jikan.moe/v4/anime/{id}/videos"
DEFAULT_TIMEOUT = 180  # yt-dlp can be slow on first call

# Varied clip durations for natural-looking edits
CLIP_DURATIONS = [2.4, 1.8, 2.6, 2.0, 1.7, 2.3, 2.1, 1.9]


# ---------------------------------------------------------------------------
# Jikan: trailer URLs
# ---------------------------------------------------------------------------

def fetch_trailer_urls(anime_id, max_count=4):
    """Return a list of YouTube URLs for the anime's promo videos."""
    try:
        r = requests.get(JIKAN_VIDEOS.format(id=anime_id), timeout=15)
        r.raise_for_status()
        data = r.json().get('data', {})

        urls = []
        # Primary: promo videos (official PVs / trailers)
        for promo in data.get('promo', [])[:max_count]:
            trailer = promo.get('trailer', {}) or {}
            url = trailer.get('url')
            if url and ('youtube.com' in url or 'youtu.be' in url):
                urls.append(url)

        # Fallback: music videos (still official, often have animation)
        if not urls:
            for mv in data.get('music_videos', [])[:max_count]:
                video = mv.get('video', {}) or {}
                url = video.get('url')
                if url and ('youtube.com' in url or 'youtu.be' in url):
                    urls.append(url)

        return urls
    except Exception as e:
        print(f"[clip_extractor] Jikan videos fetch failed: {e}")
        return []


# ---------------------------------------------------------------------------
# yt-dlp download
# ---------------------------------------------------------------------------

def download_trailer(url, output_path):
    """Download YouTube video at <=720p. Returns True on success."""
    try:
        cmd = [
            'yt-dlp',
            '-f', 'best[height<=720][ext=mp4]/best[height<=720]/best',
            '--no-playlist',
            '--no-warnings',
            '--quiet',
            '--socket-timeout', '30',
            '-o', output_path,
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=DEFAULT_TIMEOUT)
        if result.returncode == 0 and os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"[clip_extractor] Downloaded {size_mb:.1f} MB from {url[:50]}...")
            return True
        err = (result.stderr or '')[-300:]
        print(f"[clip_extractor] yt-dlp failed: {err}")
        return False
    except subprocess.TimeoutExpired:
        print(f"[clip_extractor] yt-dlp timed out after {DEFAULT_TIMEOUT}s")
        return False
    except Exception as e:
        print(f"[clip_extractor] yt-dlp exception: {e}")
        return False


# ---------------------------------------------------------------------------
# ffmpeg helpers
# ---------------------------------------------------------------------------

def _video_duration(path):
    """Return duration in seconds via ffprobe; 0 if unknown."""
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_entries',
               'format=duration', '-of',
               'default=noprint_wrappers=1:nokey=1', path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def extract_clip(input_path, start_sec, duration_sec, output_path):
    """
    Extract a 9:16 muted clip with anime color grade baked in.

      scale + crop  -> 1080x1920 (cover crop, no letterbox)
      eq filter     -> bright, vivid anime grade
      drop audio    -> our VO is the only sound in the final video
    """
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "eq=saturation=1.30:contrast=1.15:brightness=-0.04:gamma=0.95,"
        "unsharp=5:5:0.6:5:5:0.0"
    )
    cmd = [
        'ffmpeg', '-y',
        '-ss', f'{start_sec:.2f}',
        '-i', input_path,
        '-t', f'{duration_sec:.2f}',
        '-vf', vf,
        '-an',  # mute audio
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '20',
        '-pix_fmt', 'yuv420p',
        '-r', '30',
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if result.returncode != 0:
            print(f"[clip_extractor] ffmpeg extract failed: {result.stderr[-200:]}")
            return False
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 20000:
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"[clip_extractor] ffmpeg timed out on clip at t={start_sec:.1f}")
        return False


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def fetch_video_clips(anime_id, output_dir, target_clips=6, rng_seed=None):
    """
    Try to produce `target_clips` short anime clips for today's anime.
    Returns list of mp4 paths (empty list if anything fails — caller
    falls back to still images only).
    """
    if not anime_id:
        return []

    os.makedirs(output_dir, exist_ok=True)
    urls = fetch_trailer_urls(anime_id)
    if not urls:
        print(f"[clip_extractor] No trailer URLs for anime ID {anime_id}")
        return []

    print(f"[clip_extractor] Found {len(urls)} trailer URL(s)")
    trailer_path = os.path.join(output_dir, '_trailer.mp4')

    downloaded = False
    for url in urls:
        if download_trailer(url, trailer_path):
            downloaded = True
            break
        if os.path.exists(trailer_path):
            os.remove(trailer_path)

    if not downloaded:
        print("[clip_extractor] All trailer downloads failed")
        return []

    duration = _video_duration(trailer_path)
    if duration < 10:
        print(f"[clip_extractor] Trailer too short to use ({duration:.1f}s)")
        try: os.remove(trailer_path)
        except Exception: pass
        return []

    print(f"[clip_extractor] Trailer duration: {duration:.1f}s")

    # Avoid first 3s (network/logo intros) and last 5s (end cards / titles)
    usable_start = 3.0
    usable_end   = max(usable_start + 5.0, duration - 5.0)

    # If trailer is short, take fewer clips
    max_possible = int((usable_end - usable_start) / 3.0)
    target_clips = min(target_clips, max(max_possible, 2))

    # Evenly distribute clips with small random jitter so they don't
    # land in identical positions across days
    rng = random.Random(rng_seed or 'fv-clips')
    step = (usable_end - usable_start) / target_clips
    clips = []
    for i in range(target_clips):
        clip_dur = CLIP_DURATIONS[i % len(CLIP_DURATIONS)]
        jitter = rng.uniform(0, step * 0.25)
        start = usable_start + i * step + jitter
        if start + clip_dur > usable_end:
            continue
        out_path = os.path.join(output_dir, f"clip_{i:03d}.mp4")
        if extract_clip(trailer_path, start, clip_dur, out_path):
            clips.append(out_path)

    # Clean up the source trailer to save disk
    try: os.remove(trailer_path)
    except Exception: pass

    print(f"[clip_extractor] Extracted {len(clips)} usable clips")
    return clips
