import os
import math
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips,
)

# ---------------------------------------------------------------------------
# Shorts: 1080 x 1920 vertical  (9:16)
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 1080, 1920
FPS = 30
SECONDS_PER_IMAGE = 6

BRAND_COLOR = (138, 43, 226)   # Purple
TEXT_COLOR  = (255, 255, 255)
BG_DARK     = (10, 10, 20)

# Font paths (installed by workflow: fonts-liberation)
FONT_BOLD    = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Frame helpers
# ---------------------------------------------------------------------------

def prepare_background(img_path, width=WIDTH, height=HEIGHT):
    """Resize, blur and darken an image for vertical Short background."""
    img = Image.open(img_path).convert('RGB')

    # Fill frame vertically (portrait crop)
    img_ratio   = img.width / img.height
    frame_ratio = width / height
    if img_ratio > frame_ratio:
        new_h = height
        new_w = int(height * img_ratio)
    else:
        new_w = width
        new_h = int(width / img_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - width) // 2
    top  = (new_h - height) // 2
    img  = img.crop((left, top, left + width, top + height))

    img = img.filter(ImageFilter.GaussianBlur(radius=8))
    img = ImageEnhance.Brightness(img).enhance(0.30)
    return np.array(img)


def make_gradient_background(width=WIDTH, height=HEIGHT):
    """Deep purple gradient fallback when no images available."""
    img  = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / height
        r = int(10  + 128 * t * 0.4)
        g = int(10  + 33  * t * 0.4)
        b = int(20  + 206 * t * 0.4)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return np.array(img)


def add_branding_overlay(frame_array, channel_name="Fantasy Verse"):
    """
    Vertical Short overlay:
      - Top: channel name bar
      - Purple accent line
      - Bottom dark zone reserved for subtitles
    """
    img  = Image.fromarray(frame_array)
    draw = ImageDraw.Draw(img)

    # Top bar (gradient fade)
    top_bar_h = 110
    for y in range(top_bar_h):
        alpha = int(210 * (1 - y / top_bar_h))
        draw.line([(0, y), (WIDTH, y)], fill=(10, 10, 20))

    # Purple accent line
    draw.rectangle([0, top_bar_h - 4, WIDTH, top_bar_h], fill=BRAND_COLOR)

    # Channel name
    font = _font(FONT_BOLD, 46)
    draw.text((WIDTH // 2, 55), f"FANTASY VERSE", fill=TEXT_COLOR, font=font, anchor="mm")

    # Small handle below
    font_sm = _font(FONT_REGULAR, 28)
    draw.text((WIDTH // 2, 88), "@DejuShetty", fill=(200, 160, 255), font=font_sm, anchor="mm")

    # Bottom bar for subtitles (solid dark strip)
    sub_bar_top = HEIGHT - 220
    for y in range(sub_bar_top, HEIGHT):
        draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0))

    return np.array(img)


# ---------------------------------------------------------------------------
# Intro / Outro cards
# ---------------------------------------------------------------------------

def create_intro_card(duration=2):
    img  = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Animated gradient stripes
    for i in range(0, WIDTH, 5):
        c = int(138 * abs(math.sin(i * 0.007)))
        draw.line([(i, 0), (i, HEIGHT)], fill=(c // 8, c // 20, c // 4))

    font_big = _font(FONT_BOLD, 100)
    font_sub = _font(FONT_REGULAR, 48)

    draw.text((WIDTH // 2, HEIGHT // 2 - 100), "FANTASY",   fill=BRAND_COLOR, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2),        "VERSE",    fill=BRAND_COLOR, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 100),  "ANIME NEWS", fill=TEXT_COLOR, font=font_sub, anchor="mm")

    draw.rectangle(
        [WIDTH // 2 - 220, HEIGHT // 2 + 145, WIDTH // 2 + 220, HEIGHT // 2 + 149],
        fill=BRAND_COLOR,
    )

    return ImageClip(np.array(img)).set_duration(duration).fadein(0.4)


def create_outro_card(duration=3):
    img  = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    font_big   = _font(FONT_BOLD,    80)
    font_med   = _font(FONT_BOLD,    52)
    font_small = _font(FONT_REGULAR, 36)

    draw.text((WIDTH // 2, HEIGHT // 2 - 150), "THANKS FOR",    fill=TEXT_COLOR,   font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 - 50),  "WATCHING!",     fill=TEXT_COLOR,   font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 80),  "LIKE  SUBSCRIBE  COMMENT", fill=BRAND_COLOR, font=font_med, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 160), "Fantasy Verse", fill=(180, 180, 180), font=font_small, anchor="mm")

    return ImageClip(np.array(img)).set_duration(duration).fadein(0.4).fadeout(0.4)


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_video(image_paths, audio_path, srt_path, output_path):
    print("[video_assembler] Building vertical Short (1080x1920)...")

    audio          = AudioFileClip(audio_path)
    total_duration = audio.duration
    print(f"[video_assembler] Audio duration: {total_duration:.1f}s")

    # Prepare backgrounds
    if image_paths:
        backgrounds = [prepare_background(p) for p in image_paths]
    else:
        backgrounds = [make_gradient_background()]

    # Content clips
    content_clips = []
    current_t     = 0.0
    img_index     = 0

    while current_t < total_duration:
        remaining = total_duration - current_t
        clip_dur  = min(SECONDS_PER_IMAGE, remaining)
        if clip_dur < 0.1:
            break

        bg_branded = add_branding_overlay(backgrounds[img_index % len(backgrounds)])
        clip = (
            ImageClip(bg_branded)
            .set_duration(clip_dur)
            .set_start(current_t)
            .crossfadein(0.4)
        )
        content_clips.append(clip)
        current_t += clip_dur
        img_index  += 1

    # Combine intro + content + outro
    intro = create_intro_card(2)
    outro = create_outro_card(3)

    all_clips = [intro] + content_clips + [outro]
    final     = concatenate_videoclips(all_clips, method='compose', padding=-0.3)
    final     = final.set_audio(audio)

    # Export without subtitles first
    no_subs_path = output_path.replace('.mp4', '_nosubs.mp4')
    final.write_videofile(
        no_subs_path,
        fps=FPS,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        bitrate='4000k',
        threads=2,
        logger=None,
    )

    # Burn subtitles via ffmpeg
    _burn_subtitles(no_subs_path, srt_path, output_path)
    os.remove(no_subs_path)

    print(f"[video_assembler] Final Short: {output_path}")
    return output_path


def _burn_subtitles(input_path, srt_path, output_path):
    """Burn subtitles into the bottom safe zone of the vertical Short."""
    style = (
        "FontName=Liberation Sans,"
        "FontSize=28,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BackColour=&H99000000,"
        "Bold=1,"
        "BorderStyle=4,"
        "Shadow=0,"
        "MarginV=50,"
        "Alignment=2"
    )
    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-vf', f"subtitles={srt_path}:force_style='{style}'",
        '-c:a', 'copy',
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[video_assembler] ffmpeg subtitle error: {result.stderr[-500:]}")
        import shutil
        shutil.copy(input_path, output_path)
    else:
        print("[video_assembler] Subtitles burned in.")
