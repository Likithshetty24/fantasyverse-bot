"""
thumbnail_generator.py — Extra Time (football)
1280x720 thumbnail: dark pitch background + gold headline + channel mark.
"""

import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

THUMB_W, THUMB_H = 1280, 720

GOLD        = (240, 196, 60)
GOLD_BRIGHT = (255, 220, 90)
PITCH_GREEN = (32, 178, 110)
TEXT_COLOR  = (245, 248, 245)
BG_DARK     = (8, 18, 14)

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
    img = ImageEnhance.Brightness(img).enhance(0.50)
    img = ImageEnhance.Contrast(img).enhance(1.20)
    img = ImageEnhance.Color(img).enhance(1.10)
    return img


def _draw_bottom_gradient(draw):
    for y in range(THUMB_H - 160, THUMB_H):
        draw.line([(0, y), (THUMB_W, y)], fill=(0, 0, 0))


def _draw_headline(draw, text):
    lines = textwrap.wrap(text.upper(), width=12)[:2] if text else ["WORLD CUP"]
    font_size = 135 if max(len(l) for l in lines) <= 10 else 105
    font = _font(FONT_BOLD, font_size)

    total_h = len(lines) * (font_size + 16)
    y = (THUMB_H - total_h) // 2 - 10

    for line in lines:
        for dx, dy in [(-4, 4), (4, 4), (-4, -4), (4, -4), (0, 5)]:
            draw.text((THUMB_W // 2 + dx, y + dy), line, fill=(0, 0, 0), font=font, anchor="mm")
        draw.text((THUMB_W // 2, y), line, fill=GOLD_BRIGHT, font=font, anchor="mm")
        y += font_size + 16


def _draw_brand(draw):
    # Top-left pill
    font_pill = _font(FONT_BOLD, 36)
    draw.rounded_rectangle([20, 20, 250, 75], radius=10, fill=BG_DARK,
                           outline=GOLD, width=3)
    draw.text((135, 47), "WORLD CUP", fill=GOLD, font=font_pill, anchor="mm")

    # Bottom channel mark
    font_brand = _font(FONT_BOLD, 48)
    draw.text((THUMB_W // 2, THUMB_H - 48), "EXTRA TIME",
              fill=TEXT_COLOR, font=font_brand, anchor="mm")
    draw.rectangle([THUMB_W // 2 - 130, THUMB_H - 22,
                    THUMB_W // 2 + 130, THUMB_H - 19], fill=GOLD)


def generate_thumbnail(image_paths, thumbnail_text, output_path):
    if image_paths:
        try:
            bg = _prepare_bg(image_paths[0])
        except Exception:
            bg = Image.new('RGB', (THUMB_W, THUMB_H), BG_DARK)
    else:
        bg = Image.new('RGB', (THUMB_W, THUMB_H), BG_DARK)

    draw = ImageDraw.Draw(bg)
    _draw_bottom_gradient(draw)
    _draw_headline(draw, thumbnail_text)
    _draw_brand(draw)

    bg.save(output_path, 'JPEG', quality=95)
    print(f"[thumbnail_generator] Thumbnail saved: {output_path}")
    return output_path
