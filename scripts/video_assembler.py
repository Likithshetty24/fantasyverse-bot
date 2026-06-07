"""
video_assembler.py — The AI Stack
Tech-aesthetic vertical Short builder.

  * 1080x1920 vertical, 30fps, 45-60 sec
  * Cool blue/cyan color grade
  * Subtle channel watermark top-left
  * Small content-type pill top-right (NEW / EXPLAINER / TOOL / NEWS)
  * Gentle Ken Burns zoom + occasional zoom punch
  * Minimal flash cuts (less aggressive than the anime version)
  * High-quality encode (CRF 19, preset slow)
"""

import os
import math
import random
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips,
    CompositeVideoClip, ColorClip,
)

WIDTH, HEIGHT = 1080, 1920
FPS = 30


def _shot_durations():
    """Shot pacing — slightly slower than anime, content takes precedence."""
    rng = random.Random(datetime.now().strftime('%Y%m%d'))
    base = [3.5, 3.0, 2.8, 2.6, 2.4, 2.5, 2.7, 2.6, 2.8, 3.0, 3.2]
    return [round(d + rng.uniform(-0.25, 0.25), 2) for d in base]


# Tech palette — cool, modern, developer-friendly
BRAND_CYAN  = (32, 184, 220)
ACCENT_BLUE = (84, 120, 245)
TEXT_COLOR  = (240, 245, 250)
BG_DARK     = (8, 12, 20)
PILL_DARK   = (20, 28, 40)

FONT_BOLD    = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Background prep — tech color grade, soft vignette
# ---------------------------------------------------------------------------

def prepare_background(img_path):
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

    img = img.filter(ImageFilter.GaussianBlur(radius=1.5))
    img = ImageEnhance.Brightness(img).enhance(0.78)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(1.05)

    # Cool color cast: push blue, pull red slightly
    arr = np.array(img).astype(np.int16)
    arr[..., 0] = np.clip(arr[..., 0] - 6, 0, 255)
    arr[..., 2] = np.clip(arr[..., 2] + 10, 0, 255)
    arr = arr.astype(np.uint8)

    # Soft vignette
    arr = arr.astype(np.float32)
    y, x = np.ogrid[:HEIGHT, :WIDTH]
    cx, cy = WIDTH / 2, HEIGHT / 2
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    max_dist = np.sqrt(cx ** 2 + cy ** 2)
    vignette = 1.0 - 0.35 * (dist / max_dist) ** 1.5
    arr *= vignette[:, :, np.newaxis]
    arr = np.clip(arr, 0, 255).astype(np.uint8)

    return arr


def make_gradient_background():
    img  = Image.new('RGB', (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(8  + 12 * t)
        g = int(12 + 40 * t)
        b = int(20 + 80 * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return np.array(img)


# ---------------------------------------------------------------------------
# Subtle overlay: small channel mark + small type pill
# ---------------------------------------------------------------------------

def add_overlay(frame_array, banner_tag="EXPLAINER"):
    img  = Image.fromarray(frame_array)
    draw = ImageDraw.Draw(img)

    # Top-left: small channel name (no big bar)
    font_brand = _font(FONT_BOLD, 30)
    # Subtle shadow
    draw.text((32, 34), "▸ THE AI STACK", fill=(0, 0, 0), font=font_brand)
    draw.text((30, 32), "▸ THE AI STACK", fill=TEXT_COLOR, font=font_brand)

    # Tiny cyan underscore
    draw.rectangle([30, 68, 30 + 110, 71], fill=BRAND_CYAN)

    # Top-right: content type pill (NEW/EXPLAINER/TOOL/NEWS)
    if banner_tag:
        font_pill = _font(FONT_BOLD, 26)
        text = f" {banner_tag} "
        bbox = draw.textbbox((0, 0), text, font=font_pill)
        pw = bbox[2] - bbox[0] + 22
        ph = bbox[3] - bbox[1] + 16
        px = WIDTH - pw - 30
        py = 28

        # Drop shadow
        draw.rounded_rectangle([px + 2, py + 2, px + pw + 2, py + ph + 2],
                                radius=12, fill=(0, 0, 0))
        # Pill background
        draw.rounded_rectangle([px, py, px + pw, py + ph],
                                radius=12, fill=PILL_DARK,
                                outline=BRAND_CYAN, width=2)
        draw.text((px + 11, py + 6), banner_tag, fill=BRAND_CYAN, font=font_pill)

    return np.array(img)


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------

def gentle_zoom_clip(bg_array, duration):
    """Slow Ken Burns — 1.0 → 1.05 over duration."""
    clip = ImageClip(bg_array).set_duration(duration)
    def scale(t):
        return 1.0 + 0.05 * (t / duration)
    return clip.resize(scale).set_position('center')


def zoom_punch_clip(bg_array, duration):
    """Zoom-punch entry (1.18 → 1.0 in 0.25s) then drift to 1.04."""
    clip = ImageClip(bg_array).set_duration(duration)
    punch_dur = 0.25
    drift_to = 1.04
    def scale(t):
        if t < punch_dur:
            return 1.18 - (1.18 - 1.0) * (t / punch_dur)
        progress = (t - punch_dur) / max(duration - punch_dur, 0.01)
        return 1.0 + (drift_to - 1.0) * progress
    return clip.resize(scale).set_position('center')


def flash_frame(duration=0.04):
    return ColorClip(size=(WIDTH, HEIGHT),
                     color=(220, 230, 245)).set_duration(duration)


# ---------------------------------------------------------------------------
# Intro / Outro
# ---------------------------------------------------------------------------

def create_intro_card(duration=1.5):
    img  = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Subtle cyan accent lines (grid feel)
    for i in range(0, WIDTH, 90):
        draw.line([(i, 0), (i, HEIGHT)], fill=(15, 30, 50))
    for j in range(0, HEIGHT, 90):
        draw.line([(0, j), (WIDTH, j)], fill=(15, 30, 50))

    font_big = _font(FONT_BOLD, 130)
    font_sub = _font(FONT_REGULAR, 50)

    draw.text((WIDTH // 2, HEIGHT // 2 - 80), "THE AI", fill=BRAND_CYAN, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 60), "STACK",  fill=BRAND_CYAN, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 200), "daily AI for builders",
              fill=TEXT_COLOR, font=font_sub, anchor="mm")

    draw.rectangle(
        [WIDTH // 2 - 200, HEIGHT // 2 + 250, WIDTH // 2 + 200, HEIGHT // 2 + 254],
        fill=BRAND_CYAN,
    )
    return ImageClip(np.array(img)).set_duration(duration).fadein(0.25).fadeout(0.2)


def create_outro_card(duration=2.5):
    img  = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    font_big   = _font(FONT_BOLD, 80)
    font_med   = _font(FONT_BOLD, 56)
    font_small = _font(FONT_REGULAR, 38)

    draw.text((WIDTH // 2, HEIGHT // 2 - 200), "WANT MORE?",      fill=TEXT_COLOR, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 - 90),  "FOLLOW for daily", fill=BRAND_CYAN, font=font_med, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 - 20),  "AI builds & news", fill=BRAND_CYAN, font=font_med, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 130), "▸ THE AI STACK",   fill=TEXT_COLOR, font=font_med, anchor="mm")

    return ImageClip(np.array(img)).set_duration(duration).fadein(0.3).fadeout(0.3)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_video(image_paths, audio_path, output_path, banner_tag="EXPLAINER"):
    print("[video_assembler] Building tech-aesthetic AI Short...")

    audio          = AudioFileClip(audio_path)
    total_duration = audio.duration
    print(f"[video_assembler] Audio: {total_duration:.1f}s")

    if image_paths:
        backgrounds = [add_overlay(prepare_background(p), banner_tag)
                       for p in image_paths]
    else:
        backgrounds = [add_overlay(make_gradient_background(), banner_tag)]

    intro_dur = 1.5
    outro_dur = 2.5
    content_dur = max(total_duration - intro_dur + 0.5, 5.0)

    content_clips = []
    current_t = 0.0
    shot_idx = 0
    shot_durations = _shot_durations()

    while current_t < content_dur:
        remaining = content_dur - current_t
        target = shot_durations[shot_idx % len(shot_durations)]
        clip_dur = min(target, remaining)
        if clip_dur < 0.5:
            break

        bg = backgrounds[shot_idx % len(backgrounds)]
        # Alternate gentle Ken Burns and zoom-punch for variety
        if shot_idx % 3 == 0:
            shot = zoom_punch_clip(bg, clip_dur)
        else:
            shot = gentle_zoom_clip(bg, clip_dur)
        shot = shot.set_start(current_t).crossfadein(0.3)
        content_clips.append(shot)

        # Subtle flash every few shots only
        if shot_idx % 4 == 3 and remaining > target + 0.1:
            flash = flash_frame(0.04).set_start(current_t + clip_dur - 0.02)
            content_clips.append(flash)

        current_t += clip_dur
        shot_idx += 1

    intro = create_intro_card(intro_dur)
    outro = create_outro_card(outro_dur)

    content = CompositeVideoClip(content_clips, size=(WIDTH, HEIGHT)).set_duration(content_dur)
    full = concatenate_videoclips([intro, content, outro], method='compose', padding=-0.25)
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
