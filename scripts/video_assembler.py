"""
video_assembler.py — Extra Time (football)
Vertical football Short builder.

  * 1080x1920, 30fps, 45-60 sec
  * Green/gold football color grade
  * Subtle "EXTRA TIME" watermark top-left
  * Content-type pill top-right (WORLD CUP / GOAL / LEGEND / STAT)
  * Ken Burns zoom + occasional zoom punch
  * Light flash cuts
  * NO subtitles
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
    ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips,
    CompositeVideoClip, ColorClip,
)

WIDTH, HEIGHT = 1080, 1920
FPS = 30


def _shot_durations():
    # Fast cuts up front to win the first few seconds (hook retention),
    # then settle into a slightly calmer rhythm.
    rng = random.Random(datetime.now().strftime('%Y%m%d'))
    base = [1.7, 1.8, 2.0, 2.2, 2.4, 2.5, 2.7, 2.6, 2.8, 3.0, 3.0]
    return [round(d + rng.uniform(-0.2, 0.2), 2) for d in base]


# Football palette — pitch green + gold
PITCH_GREEN = (32, 178, 110)
GOLD        = (240, 196, 60)
ACCENT_DARK = (10, 30, 20)
TEXT_COLOR  = (245, 248, 245)
BG_DARK     = (8, 18, 14)
PILL_DARK   = (14, 30, 22)

FONT_BOLD    = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

# Channel name — shown ONLY on the outro card, nowhere else in the video.
# Change this one line if your channel is named differently.
CHANNEL_NAME = "Fantasy Verse"


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Background prep
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
    img = ImageEnhance.Brightness(img).enhance(0.80)
    img = ImageEnhance.Contrast(img).enhance(1.18)
    img = ImageEnhance.Color(img).enhance(1.20)

    # Soft vignette
    arr = np.array(img).astype(np.float32)
    y, x = np.ogrid[:HEIGHT, :WIDTH]
    cx, cy = WIDTH / 2, HEIGHT / 2
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    max_dist = np.sqrt(cx ** 2 + cy ** 2)
    vignette = 1.0 - 0.38 * (dist / max_dist) ** 1.5
    arr *= vignette[:, :, np.newaxis]
    return np.clip(arr, 0, 255).astype(np.uint8)


def make_gradient_background():
    img  = Image.new('RGB', (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(8  + 24 * t)
        g = int(18 + 70 * t)
        b = int(14 + 40 * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return np.array(img)


# ---------------------------------------------------------------------------
# Overlay: watermark + content pill
# ---------------------------------------------------------------------------

def add_overlay(frame_array, banner_tag="WORLD CUP"):
    img  = Image.fromarray(frame_array)
    draw = ImageDraw.Draw(img)

    # NOTE: No channel name/watermark on content frames (user request).
    # Only a news-style content pill in the top-right — that's a content
    # tag (WORLD CUP / GOAL / BREAKING), not channel branding.

    # Top-right content pill
    if banner_tag:
        font_pill = _font(FONT_BOLD, 26)
        text = f" {banner_tag} "
        bbox = draw.textbbox((0, 0), text, font=font_pill)
        pw = bbox[2] - bbox[0] + 22
        ph = bbox[3] - bbox[1] + 16
        px = WIDTH - pw - 30
        py = 28
        draw.rounded_rectangle([px + 2, py + 2, px + pw + 2, py + ph + 2],
                                radius=12, fill=(0, 0, 0))
        draw.rounded_rectangle([px, py, px + pw, py + ph],
                                radius=12, fill=PILL_DARK,
                                outline=GOLD, width=2)
        draw.text((px + 11, py + 6), banner_tag, fill=GOLD, font=font_pill)

    return np.array(img)


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------

def gentle_zoom_clip(bg_array, duration):
    clip = ImageClip(bg_array).set_duration(duration)
    def scale(t):
        return 1.0 + 0.05 * (t / duration)
    return clip.resize(scale).set_position('center')


def zoom_punch_clip(bg_array, duration):
    clip = ImageClip(bg_array).set_duration(duration)
    punch_dur = 0.25
    drift_to = 1.05
    def scale(t):
        if t < punch_dur:
            return 1.20 - (1.20 - 1.0) * (t / punch_dur)
        progress = (t - punch_dur) / max(duration - punch_dur, 0.01)
        return 1.0 + (drift_to - 1.0) * progress
    return clip.resize(scale).set_position('center')


def flash_frame(duration=0.04):
    return ColorClip(size=(WIDTH, HEIGHT), color=(240, 240, 230)).set_duration(duration)


def _overlay_stamp(banner_tag):
    """Precompute the pill overlay + a boolean mask of where it paints."""
    overlay = add_overlay(np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8), banner_tag)
    mask = (overlay.sum(axis=2) > 8)[:, :, None]  # HxWx1 bool
    return overlay, mask


def load_video_shot(path, max_duration, banner_tag):
    """
    Load a B-roll mp4, cover-crop to 1080x1920, mute, and stamp the pill.
    Returns (clip, actual_duration) or (None, 0) on failure.
    """
    try:
        vc = VideoFileClip(path).without_audio()
        actual = min(vc.duration, max_duration)
        vc = vc.subclip(0, actual)

        # cover-scale to fill the 9:16 frame, then center-crop
        if (vc.w / vc.h) > (WIDTH / HEIGHT):
            vc = vc.resize(height=HEIGHT)
        else:
            vc = vc.resize(width=WIDTH)
        vc = vc.crop(x_center=vc.w / 2, y_center=vc.h / 2, width=WIDTH, height=HEIGHT)

        overlay, mask = _overlay_stamp(banner_tag)

        def stamp(frame):
            return (frame * (~mask) + overlay * mask).astype('uint8')

        vc = vc.fl_image(stamp)
        return vc, actual
    except Exception as e:
        print(f"[video_assembler] Failed to load B-roll {path}: {e}")
        return None, 0


# ---------------------------------------------------------------------------
# Intro / Outro
# ---------------------------------------------------------------------------

def create_intro_card(banner_tag="WORLD CUP", duration=1.3):
    """Neutral hook card — NO channel name. Shows the content tag + year."""
    img  = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Pitch stripe pattern
    for j in range(0, HEIGHT, 120):
        shade = 22 if (j // 120) % 2 == 0 else 14
        draw.rectangle([0, j, WIDTH, j + 120], fill=(8, shade + 10, shade))

    font_big = _font(FONT_BOLD, 120)
    font_sub = _font(FONT_BOLD, 60)

    tag = (banner_tag or "WORLD CUP").upper()
    draw.text((WIDTH // 2, HEIGHT // 2 - 40), tag,      fill=GOLD,       font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 70), "2026",   fill=TEXT_COLOR, font=font_sub, anchor="mm")

    draw.rectangle([WIDTH // 2 - 200, HEIGHT // 2 + 130, WIDTH // 2 + 200, HEIGHT // 2 + 134], fill=GOLD)
    return ImageClip(np.array(img)).set_duration(duration).fadein(0.25).fadeout(0.2)


def create_outro_card(duration=2.5):
    img  = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    font_big = _font(FONT_BOLD, 80)
    font_med = _font(FONT_BOLD, 56)

    font_brand = _font(FONT_BOLD, 70)
    font_small = _font(FONT_BOLD, 44)

    draw.text((WIDTH // 2, HEIGHT // 2 - 210), "FOLLOW",          fill=TEXT_COLOR, font=font_med, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 - 100), CHANNEL_NAME.upper(), fill=GOLD,    font=font_brand, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 40),  "daily World Cup",  fill=TEXT_COLOR, font=font_med, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 110), "reactions",        fill=TEXT_COLOR, font=font_med, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 210), "don't miss the next shock",
              fill=GOLD, font=font_small, anchor="mm")

    return ImageClip(np.array(img)).set_duration(duration).fadein(0.3).fadeout(0.3)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_video(image_paths, audio_path, output_path, banner_tag="WORLD CUP",
                video_clip_paths=None, pre_clips=None):
    """
    image_paths      : real stills (Ken Burns)
    video_clip_paths : free B-roll mp4s, interleaved with stills (real motion)
    pre_clips        : moviepy clips (e.g. animated scoreline) shown first
    """
    print("[video_assembler] Building football Short...")
    video_clip_paths = video_clip_paths or []
    pre_clips        = pre_clips or []

    audio          = AudioFileClip(audio_path)
    total_duration = audio.duration
    print(f"[video_assembler] Audio: {total_duration:.1f}s")
    print(f"[video_assembler] Sources: {len(image_paths)} stills + "
          f"{len(video_clip_paths)} B-roll + {len(pre_clips)} graphics")

    if image_paths:
        backgrounds = [add_overlay(prepare_background(p), banner_tag) for p in image_paths]
    else:
        backgrounds = [add_overlay(make_gradient_background(), banner_tag)]

    # No intro card — open instantly on the hook (striking image / scoreline)
    # so viewers don't swipe away in the first second.
    outro_dur = 2.5
    content_dur = max(total_duration, 5.0)

    # Build an interleaved source plan: still, broll, still, still, broll...
    # (~1 B-roll every 3 shots so real motion is sprinkled through)
    sources = []
    bi = 0
    si = 0
    n_slots = 40  # plenty; we stop by time anyway
    for k in range(n_slots):
        if video_clip_paths and k % 3 == 2:
            sources.append(('video', video_clip_paths[bi % len(video_clip_paths)]))
            bi += 1
        else:
            sources.append(('image', backgrounds[si % len(backgrounds)]))
            si += 1

    content_clips = []
    current_t = 0.0
    shot_idx = 0
    shot_durations = _shot_durations()

    # Optional pre-clips (scoreline) play first inside the content timeline
    for pc in pre_clips:
        d = pc.duration
        content_clips.append(pc.set_start(current_t).crossfadein(0.2))
        current_t += d
        shot_idx += 1

    while current_t < content_dur:
        remaining = content_dur - current_t
        target = shot_durations[shot_idx % len(shot_durations)]
        clip_dur = min(target, remaining)
        if clip_dur < 0.5:
            break

        kind, src = sources[shot_idx % len(sources)]

        if kind == 'video':
            shot, actual = load_video_shot(src, clip_dur, banner_tag)
            if shot is None:
                shot_idx += 1
                continue
            shot = shot.set_start(current_t).crossfadein(0.3)
            content_clips.append(shot)
            current_t += actual
        else:
            if shot_idx % 3 == 0:
                shot = zoom_punch_clip(src, clip_dur)
            else:
                shot = gentle_zoom_clip(src, clip_dur)
            shot = shot.set_start(current_t).crossfadein(0.3)
            content_clips.append(shot)
            if shot_idx % 4 == 3 and remaining > target + 0.1:
                content_clips.append(flash_frame(0.04).set_start(current_t + clip_dur - 0.02))
            current_t += clip_dur

        shot_idx += 1

    content_dur = max(content_dur, current_t)

    outro = create_outro_card(outro_dur)

    content = CompositeVideoClip(content_clips, size=(WIDTH, HEIGHT)).set_duration(content_dur)
    full = concatenate_videoclips([content, outro], method='compose', padding=-0.25)
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
