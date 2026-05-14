"""
thumbnail_generator.py
1280x720 thumbnail for Daulat Mantra.
Dark cinematic background + big gold Hindi headline + small channel mark.
"""

import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

THUMB_W, THUMB_H = 1280, 720

GOLD        = (212, 175, 55)
GOLD_BRIGHT = (255, 215, 90)
TEXT_COLOR  = (245, 240, 225)
BG_DARK     = (10, 8, 12)

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

    img = img.filter(ImageFilter.GaussianBlur(radius=2))
    img = ImageEnhance.Brightness(img).enhance(0.45)
    img = ImageEnhance.Contrast(img).enhance(1.20)
    img = ImageEnhance.Color(img).enhance(0.85)
    return img


def _draw_dark_gradient(draw):
    """Left-side darkening for text readability."""
    for x in range(THUMB_W // 2):
        draw.line([(x, 0), (x, THUMB_H)], fill=(0, 0, 0))


def _draw_headline(draw, text):
    """Big gold Hindi headline, center-anchored."""
    lines = textwrap.wrap(text, width=10)[:2] if text else ["दौलत"]

    font_size = 140 if max(len(l) for l in lines) <= 7 else 110
    font = _font(FONT_HINDI_BOLD, font_size)

    total_h = len(lines) * (font_size + 18)
    y = (THUMB_H - total_h) // 2 - 10

    for line in lines:
        # Black stroke
        for dx, dy in [(-3, 3), (3, 3), (-3, -3), (3, -3), (0, 4)]:
            draw.text((THUMB_W // 2 + dx, y + dy), line, fill=(0, 0, 0), font=font, anchor="mm")
        # Gold fill
        draw.text((THUMB_W // 2, y), line, fill=GOLD_BRIGHT, font=font, anchor="mm")
        y += font_size + 18


def _draw_brand(draw):
    """Small channel mark bottom-center."""
    font_brand = _font(FONT_HINDI_BOLD, 42)
    draw.text((THUMB_W // 2, THUMB_H - 50), "दौलत मंत्र",
              fill=TEXT_COLOR, font=font_brand, anchor="mm")
    # Tiny gold underline
    draw.rectangle([THUMB_W // 2 - 110, THUMB_H - 22,
                    THUMB_W // 2 + 110, THUMB_H - 19], fill=GOLD)


def generate_thumbnail(image_paths, thumbnail_text, output_path):
    if image_paths:
        try:
            bg = _prepare_bg(image_paths[0])
        except Exception:
            bg = Image.new('RGB', (THUMB_W, THUMB_H), BG_DARK)
    else:
        bg = Image.new('RGB', (THUMB_W, THUMB_H), BG_DARK)

    draw = ImageDraw.Draw(bg)
    _draw_dark_gradient(draw)
    _draw_headline(draw, thumbnail_text)
    _draw_brand(draw)

    bg.save(output_path, 'JPEG', quality=95)
    print(f"[thumbnail_generator] Thumbnail saved: {output_path}")
    return output_path
