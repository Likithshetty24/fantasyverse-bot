"""
video_assembler.py
Fantasy Verse anime news Short — director-style production.

Production elements:
  * 1080x1920 vertical, 30fps, 30-60 sec
  * Fast cuts: every 1.5-2.5 sec
  * Zoom-punch entry on each new shot (rapid 1.25x → 1.0x in 0.25s)
  * White flash frames between cuts (1 frame = ~33ms)
  * Lower-third red "BREAKING" / "LEAKED" / "RUMOR" banner (top-positioned)
  * High-saturation anime color grade
  * Channel watermark top-left
  * NO subtitles, NO captions on screen
"""

import os
import math
import random
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# moviepy 1.0.3 + Pillow 10 compat shim
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip,
)

WIDTH, HEIGHT = 1080, 1920
FPS = 30

# Pacing: faster cuts later in the video for retention.
# Slightly randomised per-day so the rhythm doesn't feel mechanical.
def _shot_durations():
    rng = random.Random(datetime.now().strftime('%Y%m%d'))
    base = [3.2, 2.5, 2.2, 2.0, 1.9, 1.8, 1.7, 1.6, 1.7, 1.8, 2.0, 2.2]
    return [round(d + rng.uniform(-0.25, 0.25), 2) for d in base]

BRAND_PURPLE = (138, 43, 226)
BANNER_RED   = (220, 30, 30)
TEXT_COLOR   = (255, 255, 255)
BG_DARK      = (8, 5, 14)

FONT_BOLD    = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Background preparation
# ---------------------------------------------------------------------------

def prepare_background(img_path):
    """Crop to 9:16, mild blur, push anime saturation/contrast."""
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

    # Anime grade: bright, vibrant, slight blur for cinematic feel
    img = img.filter(ImageFilter.GaussianBlur(radius=2))
    img = ImageEnhance.Brightness(img).enhance(0.75)
    img = ImageEnhance.Contrast(img).enhance(1.20)
    img = ImageEnhance.Color(img).enhance(1.35)

    return np.array(img)


def make_gradient_background():
    """Dark purple gradient — fallback only."""
    img  = Image.new('RGB', (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(8  + 50 * t)
        g = int(5  + 10 * t)
        b = int(14 + 80 * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return np.array(img)


# ---------------------------------------------------------------------------
# Overlay (watermark + banner) — baked into each frame
# ---------------------------------------------------------------------------

def add_overlay(frame_array, banner_tag="BREAKING"):
    img  = Image.fromarray(frame_array)
    draw = ImageDraw.Draw(img)

    # Top dark gradient bar for legibility
    bar_h = 130
    for y in range(bar_h):
        alpha = int(220 * (1 - y / bar_h))
        draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0))

    # Purple accent stripe
    draw.rectangle([0, bar_h - 4, WIDTH, bar_h], fill=BRAND_PURPLE)

    # Channel name top-left
    font_brand = _font(FONT_BOLD, 38)
    draw.text((30, 30), "⚡ FANTASY VERSE", fill=TEXT_COLOR, font=font_brand)

    # Handle below
    font_handle = _font(FONT_REGULAR, 24)
    draw.text((30, 78), "Daily Anime News", fill=(200, 180, 255), font=font_handle)

    # Lower-third red BREAKING banner (positioned at ~y=180 to avoid Shorts UI)
    if banner_tag:
        banner_y = bar_h + 30
        # Red pill background
        font_banner = _font(FONT_BOLD, 56)
        tag_text = f"  {banner_tag}  "
        bbox = draw.textbbox((0, 0), tag_text, font=font_banner)
        bw = bbox[2] - bbox[0] + 30
        bh = bbox[3] - bbox[1] + 25

        bx = 30
        # Drop shadow
        draw.rectangle([bx + 4, banner_y + 4, bx + bw + 4, banner_y + bh + 4], fill=(0, 0, 0))
        # Main banner
        draw.rectangle([bx, banner_y, bx + bw, banner_y + bh], fill=BANNER_RED)
        # Tiny white tab on left edge
        draw.rectangle([bx, banner_y, bx + 8, banner_y + bh], fill=TEXT_COLOR)
        # Banner text
        draw.text((bx + 18, banner_y + 6), banner_tag, fill=TEXT_COLOR, font=font_banner)

    return np.array(img)


# ---------------------------------------------------------------------------
# Effects: zoom punch + flash cut
# ---------------------------------------------------------------------------

def zoom_punch_clip(bg_array, duration):
    """ImageClip that starts at 1.25x zoom and snaps to 1.0x in 0.25s, then slowly drifts to 1.06x."""
    clip = ImageClip(bg_array).set_duration(duration)
    punch_dur = 0.25
    drift_to = 1.06

    def scale(t):
        if t < punch_dur:
            return 1.25 - (1.25 - 1.0) * (t / punch_dur)
        # Slow drift
        progress = (t - punch_dur) / max(duration - punch_dur, 0.01)
        return 1.0 + (drift_to - 1.0) * progress

    return clip.resize(scale).set_position('center')


def flash_frame(duration=0.05):
    """White ColorClip used between shots."""
    return ColorClip(size=(WIDTH, HEIGHT), color=(255, 255, 255)).set_duration(duration)


# ---------------------------------------------------------------------------
# Intro / Outro
# ---------------------------------------------------------------------------

def create_intro_card(duration=1.8):
    img  = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Diagonal accent stripes
    for i in range(-HEIGHT, WIDTH, 12):
        c = int(60 + 40 * abs(math.sin(i * 0.02)))
        draw.line([(i, 0), (i + HEIGHT, HEIGHT)], fill=(c // 3, 0, c))

    font_big = _font(FONT_BOLD, 130)
    font_sub = _font(FONT_BOLD, 56)

    draw.text((WIDTH // 2, HEIGHT // 2 - 130), "FANTASY", fill=BRAND_PURPLE, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 20),  "VERSE",   fill=BRAND_PURPLE, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 160), "ANIME NEWS", fill=TEXT_COLOR, font=font_sub, anchor="mm")

    draw.rectangle(
        [WIDTH // 2 - 240, HEIGHT // 2 + 220, WIDTH // 2 + 240, HEIGHT // 2 + 226],
        fill=BRAND_PURPLE,
    )

    return ImageClip(np.array(img)).set_duration(duration).fadein(0.2)


def create_outro_card(duration=2.5):
    img  = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    font_big   = _font(FONT_BOLD, 85)
    font_med   = _font(FONT_BOLD, 55)
    font_small = _font(FONT_REGULAR, 38)

    draw.text((WIDTH // 2, HEIGHT // 2 - 200), "FOLLOW FOR",      fill=TEXT_COLOR, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 - 90),  "DAILY ANIME NEWS", fill=BRAND_PURPLE, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 60),  "LIKE • SUBSCRIBE • COMMENT", fill=TEXT_COLOR, font=font_med, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 170), "@FantasyVerse",   fill=(180, 160, 255), font=font_small, anchor="mm")

    return ImageClip(np.array(img)).set_duration(duration).fadein(0.2).fadeout(0.3)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_video(image_paths, audio_path, output_path, banner_tag="BREAKING"):
    print("[video_assembler] Building director-style anime Short...")

    audio          = AudioFileClip(audio_path)
    total_duration = audio.duration
    print(f"[video_assembler] Audio: {total_duration:.1f}s")

    if image_paths:
        backgrounds = [add_overlay(prepare_background(p), banner_tag) for p in image_paths]
    else:
        backgrounds = [add_overlay(make_gradient_background(), banner_tag)]

    intro_dur = 1.8
    outro_dur = 2.5
    content_dur = max(total_duration - intro_dur + 0.5, 5.0)

    # Generate content shots with zoom punch + flash cuts
    content_clips = []
    current_t = 0.0
    img_idx = 0
    shot_idx = 0
    shot_durations = _shot_durations()

    while current_t < content_dur:
        remaining = content_dur - current_t
        target = shot_durations[shot_idx % len(shot_durations)]
        clip_dur = min(target, remaining)
        if clip_dur < 0.4:
            break

        bg = backgrounds[img_idx % len(backgrounds)]
        shot = zoom_punch_clip(bg, clip_dur).set_start(current_t)
        content_clips.append(shot)

        # Flash frame between shots (skip after last shot)
        if remaining > target + 0.1:
            flash = flash_frame(0.06).set_start(current_t + clip_dur - 0.03)
            content_clips.append(flash)

        current_t += clip_dur
        img_idx += 1
        shot_idx += 1

    # Stitch: intro + content (composite) + outro
    intro = create_intro_card(intro_dur)
    outro = create_outro_card(outro_dur)

    # Content needs to be a single composite
    content = CompositeVideoClip(content_clips, size=(WIDTH, HEIGHT)).set_duration(content_dur)

    full = concatenate_videoclips([intro, content, outro], method='compose', padding=-0.2)
    full = full.set_audio(audio)

    # High-quality encode:
    #   preset=slow → better compression efficiency at given bitrate
    #   CRF 19    → visually near-lossless for YouTube
    #   pix_fmt yuv420p → universal mobile/web compatibility
    #   tune film → preserves detail in high-motion anime art
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
