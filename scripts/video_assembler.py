"""
video_assembler.py
Builds the vertical Hindi horror Short.
- 1080x1920, 30fps
- Dark color grade, red accent
- NO subtitles (full-bleed video)
- Subtle channel watermark + brief story-title flash at the start
- Slow Ken Burns zoom on each image for creeping dread
"""

import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# moviepy 1.0.3 calls Image.ANTIALIAS which was removed in Pillow 10.
# Alias to LANCZOS (functionally identical) so .resize() works.
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip,
)

WIDTH, HEIGHT = 1080, 1920
FPS = 30
SECONDS_PER_IMAGE = 5

# Horror palette
BLOOD_RED   = (180, 20, 20)
DEEP_RED    = (120, 10, 10)
TEXT_COLOR  = (240, 230, 220)
BG_DARK     = (8, 5, 8)

# Fonts — Devanagari needs Noto Sans Devanagari (installed via fonts-noto-core)
FONT_HINDI_BOLD    = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
FONT_HINDI_REGULAR = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
FONT_LATIN_BOLD    = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_LATIN_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def _font(path, size, fallback=FONT_LATIN_REGULAR):
    for p in (path, fallback):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Background prep — strong dark grade
# ---------------------------------------------------------------------------

def prepare_background(img_path):
    """Crop to 1080x1920, blur slightly, darken heavily, push reds."""
    img = Image.open(img_path).convert('RGB')

    img_ratio   = img.width / img.height
    frame_ratio = WIDTH / HEIGHT
    if img_ratio > frame_ratio:
        new_h = HEIGHT
        new_w = int(HEIGHT * img_ratio)
    else:
        new_w = WIDTH
        new_h = int(WIDTH / img_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - WIDTH) // 2
    top  = (new_h - HEIGHT) // 2
    img  = img.crop((left, top, left + WIDTH, top + HEIGHT))

    # Slight blur for cinematic feel
    img = img.filter(ImageFilter.GaussianBlur(radius=3))

    # Heavy darkening + reduced saturation
    img = ImageEnhance.Brightness(img).enhance(0.55)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(0.55)

    # Red tint overlay for horror mood
    arr = np.array(img).astype(np.int16)
    arr[..., 0] = np.clip(arr[..., 0] + 12, 0, 255)   # bump red
    arr[..., 1] = np.clip(arr[..., 1] - 8,  0, 255)   # reduce green
    arr[..., 2] = np.clip(arr[..., 2] - 5,  0, 255)   # reduce blue
    return arr.astype(np.uint8)


def make_gradient_background():
    """Deep red-black gradient — used when no images available."""
    img  = Image.new('RGB', (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(8  + 60  * t)
        g = int(4  + 4   * t)
        b = int(8  + 8   * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return np.array(img)


# ---------------------------------------------------------------------------
# Watermark overlay (small, unobtrusive)
# ---------------------------------------------------------------------------

def add_watermark(frame_array):
    """Tiny channel name in top-right corner."""
    img  = Image.fromarray(frame_array)
    draw = ImageDraw.Draw(img)

    font_hi = _font(FONT_HINDI_BOLD, 38, fallback=FONT_LATIN_BOLD)
    text = "रात की कहानियाँ"

    # Text box with red underline accent — top right
    margin_r = 36
    margin_t = 36
    bbox     = draw.textbbox((0, 0), text, font=font_hi)
    tw       = bbox[2] - bbox[0]
    th       = bbox[3] - bbox[1]

    x = WIDTH - tw - margin_r
    y = margin_t

    # Shadow
    draw.text((x + 2, y + 2), text, fill=(0, 0, 0), font=font_hi)
    draw.text((x, y),         text, fill=TEXT_COLOR, font=font_hi)
    # Red accent underline
    draw.rectangle([x, y + th + 8, x + tw, y + th + 12], fill=BLOOD_RED)

    return np.array(img)


# ---------------------------------------------------------------------------
# Intro card — 2 second story-title flash
# ---------------------------------------------------------------------------

def create_intro_card(title_text, duration=2.0):
    img  = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Slight noise / flicker pattern
    for i in range(0, WIDTH, 6):
        c = int(20 * abs(math.sin(i * 0.01)))
        draw.line([(i, 0), (i, HEIGHT)], fill=(c, c // 4, c // 4))

    font_big   = _font(FONT_HINDI_BOLD, 95, fallback=FONT_LATIN_BOLD)
    font_small = _font(FONT_HINDI_REGULAR, 42, fallback=FONT_LATIN_REGULAR)

    # Channel name big
    draw.text((WIDTH // 2, HEIGHT // 2 - 100), "रात की",     fill=BLOOD_RED,  font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 20),  "कहानियाँ",   fill=BLOOD_RED,  font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 160), "एक नई डरावनी कहानी...",
              fill=TEXT_COLOR, font=font_small, anchor="mm")

    # Red bar
    draw.rectangle(
        [WIDTH // 2 - 220, HEIGHT // 2 + 220, WIDTH // 2 + 220, HEIGHT // 2 + 224],
        fill=BLOOD_RED,
    )

    return ImageClip(np.array(img)).set_duration(duration).fadein(0.4).fadeout(0.3)


# ---------------------------------------------------------------------------
# Outro card — 3 sec subscribe CTA
# ---------------------------------------------------------------------------

def create_outro_card(duration=3.0):
    img  = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    font_big   = _font(FONT_HINDI_BOLD, 75,  fallback=FONT_LATIN_BOLD)
    font_med   = _font(FONT_HINDI_BOLD, 55,  fallback=FONT_LATIN_BOLD)
    font_small = _font(FONT_HINDI_REGULAR, 36, fallback=FONT_LATIN_REGULAR)

    draw.text((WIDTH // 2, HEIGHT // 2 - 220), "डर लगा?",          fill=TEXT_COLOR, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 - 100), "तो चैनल सब्सक्राइब करें", fill=BLOOD_RED,  font=font_med, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 0),   "और घंटी ज़रूर दबाएं",       fill=BLOOD_RED,  font=font_med, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 140), "हर रात नई कहानी",      fill=TEXT_COLOR, font=font_small, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 200), "Raat Ki Kahaniyan",  fill=(160, 160, 160), font=font_small, anchor="mm")

    return ImageClip(np.array(img)).set_duration(duration).fadein(0.4).fadeout(0.4)


# ---------------------------------------------------------------------------
# Ken Burns slow zoom effect
# ---------------------------------------------------------------------------

def _ken_burns_clip(bg_array, duration, zoom_start=1.0, zoom_end=1.08):
    """Creates a slow zoom effect on a static image."""
    clip = ImageClip(bg_array).set_duration(duration)

    def resize_func(t):
        progress = t / duration
        return zoom_start + (zoom_end - zoom_start) * progress

    return clip.resize(resize_func).set_position('center')


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_video(image_paths, audio_path, output_path, story_title=""):
    print("[video_assembler] Building horror Short (1080x1920)...")

    audio          = AudioFileClip(audio_path)
    total_duration = audio.duration
    print(f"[video_assembler] Audio duration: {total_duration:.1f}s")

    # Prepare backgrounds (with watermark baked in)
    if image_paths:
        backgrounds = [add_watermark(prepare_background(p)) for p in image_paths]
    else:
        backgrounds = [add_watermark(make_gradient_background())]

    # Reserve first 2s for intro card, rest for content + outro
    intro_dur = 2.0
    outro_dur = 3.0
    content_dur = max(total_duration - intro_dur + 1.0, 5.0)  # overlap intro slightly

    # Build content clips
    content_clips = []
    current_t = 0.0
    img_index = 0

    while current_t < content_dur:
        remaining = content_dur - current_t
        clip_dur  = min(SECONDS_PER_IMAGE, remaining)
        if clip_dur < 0.2:
            break

        bg = backgrounds[img_index % len(backgrounds)]
        clip = (
            _ken_burns_clip(bg, clip_dur)
            .set_start(current_t)
            .crossfadein(0.5)
        )
        content_clips.append(clip)
        current_t += clip_dur
        img_index += 1

    # Stitch: intro -> content -> outro
    intro = create_intro_card(story_title, intro_dur)
    outro = create_outro_card(outro_dur)

    all_clips = [intro] + content_clips + [outro]
    final = concatenate_videoclips(all_clips, method='compose', padding=-0.4)

    # Set audio (trim/extend so video ends with outro)
    final = final.set_audio(audio)

    final.write_videofile(
        output_path,
        fps=FPS,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        bitrate='4500k',
        threads=2,
        logger=None,
    )

    print(f"[video_assembler] Done: {output_path}")
    return output_path
