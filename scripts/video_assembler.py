import os
import math
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip
)

WIDTH, HEIGHT = 1920, 1080
FPS = 24
SECONDS_PER_IMAGE = 8

BRAND_COLOR = (138, 43, 226)   # Purple
TEXT_COLOR = (255, 255, 255)
BG_DARK = (10, 10, 20)


def prepare_background(img_path, width=WIDTH, height=HEIGHT):
    """Resize, blur and darken an image for use as background."""
    img = Image.open(img_path).convert('RGB')

    # Fill frame (crop to aspect ratio)
    img_ratio = img.width / img.height
    frame_ratio = width / height
    if img_ratio > frame_ratio:
        new_h = height
        new_w = int(height * img_ratio)
    else:
        new_w = width
        new_h = int(width / img_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Center crop
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    img = img.crop((left, top, left + width, top + height))

    # Blur + darken for readability
    img = img.filter(ImageFilter.GaussianBlur(radius=6))
    img = ImageEnhance.Brightness(img).enhance(0.35)
    return np.array(img)


def make_gradient_background(width=WIDTH, height=HEIGHT):
    """Fallback: deep purple gradient when no images available."""
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        r = int(10 + (138 - 10) * y / height * 0.4)
        g = int(10 + (43 - 10) * y / height * 0.4)
        b = int(20 + (226 - 20) * y / height * 0.4)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return np.array(img)


def add_branding_overlay(frame_array, channel_name="Fantasy Verse Anime News"):
    """Add top banner and bottom subtitle bar to a frame."""
    img = Image.fromarray(frame_array)
    draw = ImageDraw.Draw(img)

    # Top gradient bar
    bar_height = 80
    for y in range(bar_height):
        alpha = int(200 * (1 - y / bar_height))
        draw.line([(0, y), (WIDTH, y)], fill=(10, 10, 20))

    # Bottom bar for subtitles
    bottom_bar_top = HEIGHT - 120
    for y in range(bottom_bar_top, HEIGHT):
        draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0))

    # Purple accent line under top bar
    draw.rectangle([0, bar_height - 3, WIDTH, bar_height], fill=BRAND_COLOR)

    # Channel name top-left
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 32)
    except Exception:
        font = ImageFont.load_default()

    draw.text((30, 22), f"⚡ {channel_name.upper()}", fill=TEXT_COLOR, font=font)

    return np.array(img)


def create_intro_card(duration=3):
    """Creates an animated intro title card."""
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Gradient lines
    for i in range(0, WIDTH, 4):
        c = int(138 * abs(math.sin(i * 0.005)))
        draw.line([(i, 0), (i, HEIGHT)], fill=(c // 8, c // 20, c // 4))

    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 90)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 40)
    except Exception:
        font_big = ImageFont.load_default()
        font_sub = font_big

    # Center text
    title = "FANTASY VERSE"
    subtitle = "ANIME NEWS"

    draw.text((WIDTH // 2, HEIGHT // 2 - 80), title, fill=BRAND_COLOR, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 40), subtitle, fill=TEXT_COLOR, font=font_sub, anchor="mm")

    # Purple underline
    draw.rectangle([WIDTH // 2 - 200, HEIGHT // 2 + 80, WIDTH // 2 + 200, HEIGHT // 2 + 84], fill=BRAND_COLOR)

    return ImageClip(np.array(img)).set_duration(duration).fadein(0.5)


def create_outro_card(duration=4):
    """Creates a subscribe CTA outro card."""
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 72)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 45)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 32)
    except Exception:
        font_big = ImageFont.load_default()
        font_med = font_big
        font_small = font_big

    draw.text((WIDTH // 2, HEIGHT // 2 - 120), "THANKS FOR WATCHING!", fill=TEXT_COLOR, font=font_big, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 - 20), "👍  LIKE  •  SUBSCRIBE  •  COMMENT", fill=BRAND_COLOR, font=font_med, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 60), "Fantasy Verse", fill=(180, 180, 180), font=font_small, anchor="mm")

    return ImageClip(np.array(img)).set_duration(duration).fadein(0.5).fadeout(0.5)


def build_video(image_paths, audio_path, srt_path, output_path):
    print("[video_assembler] Building video...")

    audio = AudioFileClip(audio_path)
    total_duration = audio.duration
    print(f"[video_assembler] Audio duration: {total_duration:.1f}s")

    # Prepare background frames
    if image_paths:
        backgrounds = [prepare_background(p) for p in image_paths]
    else:
        backgrounds = [make_gradient_background()]

    # Create content clips (filling audio duration)
    content_clips = []
    current_t = 0.0
    img_index = 0

    while current_t < total_duration:
        remaining = total_duration - current_t
        clip_dur = min(SECONDS_PER_IMAGE, remaining)
        if clip_dur < 0.1:
            break

        bg = backgrounds[img_index % len(backgrounds)]
        bg_branded = add_branding_overlay(bg)

        clip = (ImageClip(bg_branded)
                .set_duration(clip_dur)
                .set_start(current_t)
                .crossfadein(0.5))
        content_clips.append(clip)
        current_t += clip_dur
        img_index += 1

    # Assemble: intro + content + outro
    intro = create_intro_card(3)
    outro = create_outro_card(4)

    all_clips = [intro] + content_clips + [outro]
    final = concatenate_videoclips(all_clips, method='compose', padding=-0.3)
    final = final.set_audio(audio)

    # Export without subtitles
    no_subs_path = output_path.replace('.mp4', '_nosubs.mp4')
    final.write_videofile(
        no_subs_path,
        fps=FPS,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        bitrate='3000k',
        threads=2,
        logger=None,
    )

    # Burn in subtitles with ffmpeg
    _burn_subtitles(no_subs_path, srt_path, output_path)
    os.remove(no_subs_path)

    print(f"[video_assembler] Final video: {output_path}")
    return output_path


def _burn_subtitles(input_path, srt_path, output_path):
    style = (
        "FontName=Liberation Sans,"
        "FontSize=22,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BackColour=&H90000000,"
        "Bold=1,"
        "BorderStyle=4,"
        "Shadow=0,"
        "MarginV=35"
    )
    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-vf', f"subtitles={srt_path}:force_style='{style}'",
        '-c:a', 'copy',
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[video_assembler] ffmpeg subtitle error: {result.stderr[-500:]}")
        # Fall back: just copy without subtitles
        import shutil
        shutil.copy(input_path, output_path)
    else:
        print("[video_assembler] Subtitles burned in successfully")
