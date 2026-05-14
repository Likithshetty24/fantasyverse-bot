"""
video_assembler.py
Daulat Mantra — clean cinematic Hindi mindset Shorts.

Design principles:
  * 1080x1920 vertical, 30fps, 45-65 sec
  * NO channel watermark / NO banner / NO subtitles burned in
  * Cinematic color grade (slight warm shadows, lifted blacks)
  * Slow Ken Burns drift + gentle zoom punches (less aggressive than anime version)
  * Soft vignette for cinematic feel
  * Minimal intro card (1.2 sec) + simple outro CTA (2 sec)
"""

import os
import math
import random
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# Pillow 10 / moviepy 1.0.3 compat shim
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips,
    CompositeVideoClip, ColorClip,
)

WIDTH, HEIGHT = 1080, 1920
FPS = 30

# Slightly slower pacing than anime version — mindset content needs gravitas
def _shot_durations():
    rng = random.Random(datetime.now().strftime('%Y%m%d'))
    base = [4.0, 3.5, 3.2, 3.0, 2.8, 3.0, 3.2, 3.5, 3.0, 2.8, 3.2]
    return [round(d + rng.uniform(-0.3, 0.3), 2) for d in base]


# Color palette
GOLD       = (212, 175, 55)
TEXT_COLOR = (245, 240, 225)
BG_DARK    = (10, 8, 12)

FONT_HINDI_BOLD    = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
FONT_HINDI_REGULAR = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
FONT_LATIN_BOLD    = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def _font(path, size, fallback=FONT_LATIN_BOLD):
    for p in (path, fallback):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Background preparation — cinematic grade, soft vignette, NO overlays
# ---------------------------------------------------------------------------

def prepare_background(img_path):
    """Crop to 9:16, apply cinematic grade with soft vignette. No text/banner."""
    img = Image.open(img_path).convert('RGB')

    img_r   = img.width / img.height
    frame_r = WIDTH / HEIGHT
    if img_r > frame_r:
        new_h = HEIGHT
        new_w = int(HEIGHT * img_r)
    else:
        new_w = WIDTH
        new_h = int(WIDTH / img_r)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - WIDTH) // 2
    top  = (new_h - HEIGHT) // 2
    img  = img.crop((left, top, left + WIDTH, top + HEIGHT))

    # Cinematic grade: slight blur, lifted shadows, warm cast, deeper contrast
    img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
    img = ImageEnhance.Brightness(img).enhance(0.82)
    img = ImageEnhance.Contrast(img).enhance(1.18)
    img = ImageEnhance.Color(img).enhance(1.10)

    # Apply a soft radial vignette
    arr = np.array(img).astype(np.float32)
    y, x = np.ogrid[:HEIGHT, :WIDTH]
    cx, cy = WIDTH / 2, HEIGHT / 2
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    max_dist = np.sqrt(cx ** 2 + cy ** 2)
    # vignette is 1.0 at center, ~0.55 at corners
    vignette = 1.0 - 0.45 * (dist / max_dist) ** 1.6
    arr *= vignette[:, :, np.newaxis]
    arr = np.clip(arr, 0, 255).astype(np.uint8)

    return arr


def make_gradient_background():
    """Dark warm gradient — fallback."""
    img  = Image.new('RGB', (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(10 + 40 * t)
        g = int(8  + 25 * t)
        b = int(12 + 10 * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return np.array(img)


# ---------------------------------------------------------------------------
# Subtle Ken Burns + zoom punch (gentler than anime version)
# ---------------------------------------------------------------------------

def make_clip(bg_array, duration):
    """ImageClip with a subtle zoom-in (1.0 -> 1.06) over its duration."""
    clip = ImageClip(bg_array).set_duration(duration)

    def scale(t):
        progress = t / duration
        # Soft easing
        return 1.0 + 0.06 * progress

    return clip.resize(scale).set_position('center')


# ---------------------------------------------------------------------------
# Minimal intro + outro
# ---------------------------------------------------------------------------

def create_intro_card(duration=1.2):
    img  = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    font_big   = _font(FONT_HINDI_BOLD, 130, fallback=FONT_LATIN_BOLD)
    font_sub   = _font(FONT_HINDI_REGULAR, 50)

    draw.text((WIDTH // 2, HEIGHT // 2 - 80), "दौलत",   fill=GOLD,        font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 50), "मंत्र",   fill=GOLD,        font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 180), "रोज़ की सीख", fill=TEXT_COLOR, font=font_sub, anchor="mm")

    draw.rectangle(
        [WIDTH // 2 - 180, HEIGHT // 2 + 230, WIDTH // 2 + 180, HEIGHT // 2 + 234],
        fill=GOLD,
    )

    return ImageClip(np.array(img)).set_duration(duration).fadein(0.3).fadeout(0.3)


def create_outro_card(duration=2.5):
    img  = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    font_big   = _font(FONT_HINDI_BOLD, 78, fallback=FONT_LATIN_BOLD)
    font_med   = _font(FONT_HINDI_BOLD, 56)
    font_small = _font(FONT_HINDI_REGULAR, 36)

    draw.text((WIDTH // 2, HEIGHT // 2 - 200), "रोज़ चाहिए",     fill=TEXT_COLOR, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 - 100), "ऐसी समझदारी?",  fill=TEXT_COLOR, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 50),  "Follow करो",     fill=GOLD,       font=font_med, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 130), "दौलत मंत्र",     fill=GOLD,       font=font_med, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 220), "रोज़ नई सीख",    fill=(180, 175, 160), font=font_small, anchor="mm")

    return ImageClip(np.array(img)).set_duration(duration).fadein(0.4).fadeout(0.4)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_video(image_paths, audio_path, output_path):
    print("[video_assembler] Building cinematic Hindi mindset Short...")

    audio          = AudioFileClip(audio_path)
    total_duration = audio.duration
    print(f"[video_assembler] Audio: {total_duration:.1f}s")

    if image_paths:
        backgrounds = [prepare_background(p) for p in image_paths]
    else:
        backgrounds = [make_gradient_background()]

    intro_dur   = 1.2
    outro_dur   = 2.5
    content_dur = max(total_duration - intro_dur + 0.4, 5.0)

    shot_durations = _shot_durations()
    content_clips = []
    current_t = 0.0
    img_idx = 0
    shot_idx = 0

    while current_t < content_dur:
        remaining = content_dur - current_t
        target = shot_durations[shot_idx % len(shot_durations)]
        clip_dur = min(target, remaining)
        if clip_dur < 0.5:
            break

        bg = backgrounds[img_idx % len(backgrounds)]
        shot = (
            make_clip(bg, clip_dur)
            .set_start(current_t)
            .crossfadein(0.5)
        )
        content_clips.append(shot)
        current_t += clip_dur
        img_idx += 1
        shot_idx += 1

    intro = create_intro_card(intro_dur)
    outro = create_outro_card(outro_dur)

    content = CompositeVideoClip(content_clips, size=(WIDTH, HEIGHT)).set_duration(content_dur)
    full = concatenate_videoclips([intro, content, outro], method='compose', padding=-0.3)
    full = full.set_audio(audio)

    full.write_videofile(
        output_path,
        fps=FPS,
        codec='libx264',
        audio_codec='aac',
        audio_bitrate='192k',
        preset='slow',
        threads=2,
        logger=None,
        ffmpeg_params=[
            '-crf', '19',
            '-pix_fmt', 'yuv420p',
            '-tune', 'film',
            '-movflags', '+faststart',
            '-profile:v', 'high',
            '-level', '4.2',
        ],
    )

    print(f"[video_assembler] Done: {output_path}")
    return output_path
