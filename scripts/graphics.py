"""
graphics.py — Extra Time
Self-generated animated broadcast graphics (free, legal, on-brand).

Currently: an animated scoreline card for match reaction videos — the
scores count up over ~1.2s then hold, like a TV scorebug reveal.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1920

GOLD       = (240, 196, 60)
TEXT_COLOR = (245, 248, 245)
BG_DARK    = (8, 18, 14)
GREEN_BAR  = (16, 60, 38)

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def _font(size):
    try:
        return ImageFont.truetype(FONT_BOLD, size)
    except Exception:
        return ImageFont.load_default()


def _truncate(name, n=14):
    return name if len(name) <= n else name[:n - 1] + "…"


def make_scoreline_clip(home, away, home_score, away_score,
                        phase="FULL TIME", duration=2.6):
    """
    Returns a moviepy VideoClip: an animated scoreboard reveal.
    Scores tick up from 0 over the first ~1.2s, then hold.
    """
    from moviepy.editor import VideoClip

    home_t = _truncate(home.upper())
    away_t = _truncate(away.upper())
    f_label = _font(46)
    f_team  = _font(70)
    f_score = _font(150)
    f_dash  = _font(110)

    cy = HEIGHT // 2

    def make_frame(t):
        img = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
        draw = ImageDraw.Draw(img)

        # pitch-stripe backdrop
        for j in range(0, HEIGHT, 120):
            shade = 22 if (j // 120) % 2 == 0 else 14
            draw.rectangle([0, j, WIDTH, j + 120], fill=(8, shade + 10, shade))

        # phase label
        draw.text((WIDTH // 2, cy - 320), phase.upper(), fill=GOLD, font=f_label, anchor="mm")

        # animated scores
        prog = min(t / 1.2, 1.0)
        ch = round(home_score * prog)
        ca = round(away_score * prog)

        draw.text((WIDTH // 2 - 230, cy), str(ch), fill=TEXT_COLOR, font=f_score, anchor="mm")
        draw.text((WIDTH // 2,       cy), "-",      fill=GOLD,       font=f_dash,  anchor="mm")
        draw.text((WIDTH // 2 + 230, cy), str(ca), fill=TEXT_COLOR, font=f_score, anchor="mm")

        # team names
        draw.text((WIDTH // 2 - 230, cy + 150), home_t, fill=TEXT_COLOR, font=f_team, anchor="mm")
        draw.text((WIDTH // 2 + 230, cy + 150), away_t, fill=TEXT_COLOR, font=f_team, anchor="mm")

        # gold underline
        draw.rectangle([WIDTH // 2 - 260, cy + 230, WIDTH // 2 + 260, cy + 236], fill=GOLD)

        return np.array(img)

    return VideoClip(make_frame, duration=duration).fadein(0.3).fadeout(0.25)
