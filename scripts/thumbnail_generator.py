"""
thumbnail_generator.py
Generates a 1280x720 YouTube thumbnail with:
  - Anime artwork background (blurred/darkened)
  - Gradient overlay for readability
  - Bold channel branding
  - Dynamic thumbnail text
"""

import os
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

THUMB_W, THUMB_H = 1280, 720

BRAND_COLOR   = (138, 43, 226)    # purple
ACCENT_COLOR  = (255, 200, 0)     # gold
TEXT_COLOR    = (255, 255, 255)
BG_DARK       = (10, 10, 20)

FONT_BOLD    = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _prepare_bg(img_path):
    img = Image.open(img_path).convert('RGB')

    # Cover crop to 1280x720
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

    # Mild blur + darken
    img = img.filter(ImageFilter.GaussianBlur(radius=4))
    img = ImageEnhance.Brightness(img).enhance(0.45)
    return img


def _draw_gradient_overlay(draw):
    """Dark left-side gradient so text is always readable."""
    for x in range(THUMB_W // 2):
        alpha = int(180 * (1 - x / (THUMB_W // 2)))
        draw.line([(x, 0), (x, THUMB_H)], fill=(0, 0, 0))
    # Right side partial fade
    for x in range(THUMB_W // 2, THUMB_W):
        alpha = int(90 * (x - THUMB_W // 2) / (THUMB_W // 2))
        draw.line([(x, 0), (x, THUMB_H)], fill=(0, 0, int(alpha * 0.3)))


def _draw_thumbnail_text(draw, thumb_text):
    """Large bold thumbnail headline — wraps at 2 lines max."""
    lines = textwrap.wrap(thumb_text.upper(), width=14)[:2]

    font_size = 110 if max(len(l) for l in lines) <= 10 else 88
    font = _font(FONT_BOLD, font_size)

    total_h = len(lines) * (font_size + 12)
    y_start = (THUMB_H - total_h) // 2 - 30

    for line in lines:
        # Shadow
        draw.text((62, y_start + 4), line, fill=(0, 0, 0), font=font)
        draw.text((60, y_start),     line, fill=TEXT_COLOR, font=font)
        y_start += font_size + 12


def _draw_branding(draw):
    """Bottom-left channel badge."""
    badge_x, badge_y = 40, THUMB_H - 80

    # Purple pill background
    draw.rounded_rectangle(
        [badge_x - 10, badge_y - 8, badge_x + 320, badge_y + 46],
        radius=10,
        fill=BRAND_COLOR,
    )
    font = _font(FONT_BOLD, 32)
    draw.text((badge_x + 4, badge_y + 2), "FANTASY VERSE", fill=TEXT_COLOR, font=font)


def _draw_breaking_badge(draw):
    """Top-right 'BREAKING' badge for visual pop."""
    bx, by = THUMB_W - 240, 30
    draw.rounded_rectangle([bx, by, bx + 200, by + 52], radius=8, fill=ACCENT_COLOR)
    font = _font(FONT_BOLD, 30)
    draw.text((bx + 100, by + 26), "BREAKING NEWS", fill=(0, 0, 0), font=font, anchor="mm")


def generate_thumbnail(image_paths, thumbnail_text, output_path):
    """
    Generate a 1280x720 YouTube thumbnail.

    Args:
        image_paths:    List of local image paths (first one used as background)
        thumbnail_text: Short punchy text from script_generator (e.g. 'HUGE ANIME NEWS')
        output_path:    Path to save the thumbnail JPEG
    """
    # Background
    if image_paths:
        try:
            bg = _prepare_bg(image_paths[0])
        except Exception:
            bg = Image.new('RGB', (THUMB_W, THUMB_H), BG_DARK)
    else:
        bg = Image.new('RGB', (THUMB_W, THUMB_H), BG_DARK)

    draw = ImageDraw.Draw(bg)

    # Layers
    _draw_gradient_overlay(draw)
    _draw_thumbnail_text(draw, thumbnail_text or "ANIME NEWS TODAY")
    _draw_branding(draw)
    _draw_breaking_badge(draw)

    bg.save(output_path, 'JPEG', quality=95)
    print(f"[thumbnail_generator] Thumbnail saved: {output_path}")
    return output_path
