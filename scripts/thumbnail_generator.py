"""
thumbnail_generator.py
1280x720 thumbnail for Fantasy Verse anime news Shorts.
Bold yellow text with black stroke + red BREAKING badge.
"""

import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

THUMB_W, THUMB_H = 1280, 720

BRAND_PURPLE = (138, 43, 226)
ACCENT_YELLOW = (255, 220, 0)
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

    img = img.filter(ImageFilter.GaussianBlur(radius=2))
    img = ImageEnhance.Brightness(img).enhance(0.55)
    img = ImageEnhance.Color(img).enhance(1.25)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    return img


def _draw_thumbnail_text(draw, text):
    """Large yellow Hindi-style text with thick black stroke."""
    lines = textwrap.wrap(text.upper(), width=12)[:2] if text else ["BREAKING ANIME NEWS"]

    font_size = 130 if max(len(l) for l in lines) <= 10 else 100
    font = _font(FONT_BOLD, font_size)

    total_h = len(lines) * (font_size + 16)
    y       = (THUMB_H - total_h) // 2 + 20

    for line in lines:
        # Thick black stroke
        for dx, dy in [(-4, 4), (4, 4), (-4, -4), (4, -4), (-4, 0), (4, 0), (0, -4), (0, 4)]:
            draw.text((THUMB_W // 2 + dx, y + dy), line, fill=(0, 0, 0), font=font, anchor="mm")
        # Yellow fill
        draw.text((THUMB_W // 2, y), line, fill=ACCENT_YELLOW, font=font, anchor="mm")
        y += font_size + 16


def _draw_brand(draw):
    # Top-left BREAKING badge
    font_tag = _font(FONT_BOLD, 42)
    draw.rectangle([20, 25, 320, 85], fill=BANNER_RED)
    draw.rectangle([20, 25, 30, 85], fill=TEXT_COLOR)
    draw.text((40, 32), "BREAKING", fill=TEXT_COLOR, font=font_tag)

    # Bottom channel name
    font_brand = _font(FONT_BOLD, 48)
    draw.text((THUMB_W // 2, THUMB_H - 50), "⚡ FANTASY VERSE",
              fill=TEXT_COLOR, font=font_brand, anchor="mm")


def generate_thumbnail(image_paths, thumbnail_text, output_path):
    if image_paths:
        try:
            bg = _prepare_bg(image_paths[0])
        except Exception:
            bg = Image.new('RGB', (THUMB_W, THUMB_H), BG_DARK)
    else:
        bg = Image.new('RGB', (THUMB_W, THUMB_H), BG_DARK)

    draw = ImageDraw.Draw(bg)
    _draw_thumbnail_text(draw, thumbnail_text)
    _draw_brand(draw)

    bg.save(output_path, 'JPEG', quality=95)
    print(f"[thumbnail_generator] Thumbnail saved: {output_path}")
    return output_path
