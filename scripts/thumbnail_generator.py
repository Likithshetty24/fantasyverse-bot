"""
thumbnail_generator.py — The AI Stack
1280x720 thumbnail for tech/AI Shorts.
Dark cinematic background + big cyan headline + small channel mark.
"""

import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

THUMB_W, THUMB_H = 1280, 720

BRAND_CYAN   = (32, 184, 220)
CYAN_BRIGHT  = (90, 220, 255)
TEXT_COLOR   = (240, 245, 250)
BG_DARK      = (8, 12, 20)

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


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
    img = ImageEnhance.Brightness(img).enhance(0.45)
    img = ImageEnhance.Contrast(img).enhance(1.20)
    img = ImageEnhance.Color(img).enhance(0.85)
    return img


def _draw_overlay_grid(draw):
    """Subtle tech-grid pattern over the whole thumbnail."""
    for i in range(0, THUMB_W, 80):
        draw.line([(i, 0), (i, THUMB_H)], fill=(20, 35, 55))
    for j in range(0, THUMB_H, 80):
        draw.line([(0, j), (THUMB_W, j)], fill=(20, 35, 55))


def _draw_headline(draw, text):
    """Big cyan headline center-anchored with thick stroke."""
    lines = textwrap.wrap(text.upper(), width=12)[:2] if text else ["AI EXPLAINED"]
    font_size = 130 if max(len(l) for l in lines) <= 10 else 100
    font = _font(FONT_BOLD, font_size)

    total_h = len(lines) * (font_size + 16)
    y       = (THUMB_H - total_h) // 2

    for line in lines:
        for dx, dy in [(-4, 4), (4, 4), (-4, -4), (4, -4), (0, 5)]:
            draw.text((THUMB_W // 2 + dx, y + dy), line, fill=(0, 0, 0), font=font, anchor="mm")
        draw.text((THUMB_W // 2, y), line, fill=CYAN_BRIGHT, font=font, anchor="mm")
        y += font_size + 16


def _draw_brand(draw):
    """Small bottom channel mark + corner pill."""
    # Top-left corner pill
    font_pill = _font(FONT_BOLD, 36)
    draw.rounded_rectangle([20, 20, 220, 75], radius=10, fill=BG_DARK,
                           outline=BRAND_CYAN, width=3)
    draw.text((120, 47), "DAILY AI", fill=BRAND_CYAN, font=font_pill, anchor="mm")

    # Bottom channel name
    font_brand = _font(FONT_BOLD, 48)
    draw.text((THUMB_W // 2, THUMB_H - 50), "▸ THE AI STACK",
              fill=TEXT_COLOR, font=font_brand, anchor="mm")
    draw.rectangle([THUMB_W // 2 - 150, THUMB_H - 23,
                    THUMB_W // 2 + 150, THUMB_H - 20], fill=BRAND_CYAN)


def generate_thumbnail(image_paths, thumbnail_text, output_path):
    if image_paths:
        try:
            bg = _prepare_bg(image_paths[0])
        except Exception:
            bg = Image.new('RGB', (THUMB_W, THUMB_H), BG_DARK)
    else:
        bg = Image.new('RGB', (THUMB_W, THUMB_H), BG_DARK)

    draw = ImageDraw.Draw(bg)
    _draw_overlay_grid(draw)
    _draw_headline(draw, thumbnail_text)
    _draw_brand(draw)

    bg.save(output_path, 'JPEG', quality=95)
    print(f"[thumbnail_generator] Thumbnail saved: {output_path}")
    return output_path
