"""
thumbnail_generator.py
1280x720 thumbnail for Raat Ki Kahaniyan horror Shorts.
Dark + blood-red + Hindi text.
"""

import os
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

THUMB_W, THUMB_H = 1280, 720

BLOOD_RED   = (190, 25, 25)
TEXT_COLOR  = (245, 235, 220)
BG_DARK     = (8, 5, 8)

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


def _prepare_bg(img_path):
    img = Image.open(img_path).convert('RGB')

    iw, ih   = img.size
    target_r = THUMB_W / THUMB_H
    src_r    = iw / ih
    if src_r > target_r:
        new_h = THUMB_H
        new_w = int(THUMB_H * src_r)
    else:
        new_w = THUMB_W
        new_h = int(THUMB_W / src_r)
    img  = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - THUMB_W) // 2
    top  = (new_h - THUMB_H) // 2
    img  = img.crop((left, top, left + THUMB_W, top + THUMB_H))

    img = img.filter(ImageFilter.GaussianBlur(radius=3))
    img = ImageEnhance.Brightness(img).enhance(0.4)
    img = ImageEnhance.Contrast(img).enhance(1.2)
    img = ImageEnhance.Color(img).enhance(0.6)
    return img


def _draw_vignette(draw):
    """Dark vignette around edges to focus center."""
    # Top-bottom dark fades
    for y in range(120):
        alpha = int(170 * (1 - y / 120))
        draw.line([(0, y), (THUMB_W, y)], fill=(0, 0, 0))
    for y in range(THUMB_H - 120, THUMB_H):
        alpha = int(170 * (1 - (THUMB_H - y) / 120))
        draw.line([(0, y), (THUMB_W, y)], fill=(0, 0, 0))


def _draw_thumbnail_text(draw, text):
    """Big bold red Hindi text in center."""
    lines = textwrap.wrap(text, width=10)[:2] if text else ["डरावनी कहानी"]

    font_size = 130 if max(len(l) for l in lines) <= 6 else 100
    font = _font(FONT_HINDI_BOLD, font_size)

    total_h = len(lines) * (font_size + 20)
    y       = (THUMB_H - total_h) // 2 - 20

    for line in lines:
        # Black shadow (heavy)
        for dx, dy in [(-3, 3), (3, 3), (-3, -3), (3, -3), (0, 5)]:
            draw.text((THUMB_W // 2 + dx, y + dy), line, fill=(0, 0, 0), font=font, anchor="mm")
        # Red text
        draw.text((THUMB_W // 2, y), line, fill=BLOOD_RED, font=font, anchor="mm")
        y += font_size + 20


def _draw_brand(draw):
    """Channel name bottom + tagline top."""
    # Top tagline
    font_tag = _font(FONT_HINDI_BOLD, 38)
    draw.rectangle([20, 25, 360, 80], fill=BLOOD_RED)
    draw.text((30, 32), "सच्ची कहानी", fill=TEXT_COLOR, font=font_tag)

    # Bottom channel name
    font_brand = _font(FONT_HINDI_BOLD, 44)
    draw.text((THUMB_W // 2, THUMB_H - 50), "रात की कहानियाँ",
              fill=TEXT_COLOR, font=font_brand, anchor="mm")


def generate_thumbnail(image_paths, thumbnail_text, output_path):
    """Generate 1280x720 horror thumbnail."""
    if image_paths:
        try:
            bg = _prepare_bg(image_paths[0])
        except Exception:
            bg = Image.new('RGB', (THUMB_W, THUMB_H), BG_DARK)
    else:
        bg = Image.new('RGB', (THUMB_W, THUMB_H), BG_DARK)

    draw = ImageDraw.Draw(bg)
    _draw_vignette(draw)
    _draw_thumbnail_text(draw, thumbnail_text)
    _draw_brand(draw)

    bg.save(output_path, 'JPEG', quality=95)
    print(f"[thumbnail_generator] Thumbnail saved: {output_path}")
    return output_path
