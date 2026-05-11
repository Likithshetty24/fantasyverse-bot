"""
trend_picker.py
Picks today's video topic by combining "what's trending right now"
with "is there fresh news about it".

Strategy:
  1. Pull top ~25 currently-airing anime from Jikan (this season + cross-season)
     sorted by member count → these are the truly trending shows
  2. Pull recent ANN news headlines
  3. Cross-reference: if any of today's news matches a trending anime, use that
     pairing — best content (rides trend + has news hook)
  4. Otherwise pick the top trending anime and rotate through evergreen
     content formats (character spotlight, top moments, power scaling, etc.)

Output is a single 'topic' dict that downstream modules consume.
"""

import re
import time
import requests
import feedparser
from html import unescape
from datetime import datetime

JIKAN_SEASON_NOW  = "https://api.jikan.moe/v4/seasons/now"
JIKAN_TOP_AIRING  = "https://api.jikan.moe/v4/top/anime"
ANN_RSS           = "https://www.animenewsnetwork.com/news/rss.xml"
JIKAN_DELAY       = 0.4

EXCLUDE_NEWS_KEYWORDS = ['review', 'encyclopedia', 'preview guide', 'this week in anime', 'shelf life']

# Evergreen content formats — rotated when no trending anime has news today
CONTENT_TYPES = [
    'character_spotlight',
    'top_moments',
    'power_scaling',
    'lore_drop',
    'manga_vs_anime',
    'why_trending',
]


# ---------------------------------------------------------------------------
# Trending anime fetch
# ---------------------------------------------------------------------------

def _fetch_seasonal_top():
    """This season's anime sorted by popularity (member count)."""
    try:
        r = requests.get(JIKAN_SEASON_NOW,
                         params={'limit': 25, 'sfw': 'true'},
                         timeout=15)
        r.raise_for_status()
        items = r.json().get('data', [])
        items.sort(key=lambda x: x.get('members', 0), reverse=True)
        return items[:15]
    except Exception as e:
        print(f"[trend_picker] Seasonal top fetch failed: {e}")
        return []


def _fetch_top_airing():
    """All currently-airing anime including long-runners (One Piece etc)."""
    try:
        r = requests.get(JIKAN_TOP_AIRING,
                         params={'filter': 'airing', 'limit': 15},
                         timeout=15)
        r.raise_for_status()
        return r.json().get('data', [])
    except Exception as e:
        print(f"[trend_picker] Top airing fetch failed: {e}")
        return []


def _merge_trending(seasonal, airing):
    """Dedupe by mal_id, prefer seasonal entries (fresher metadata)."""
    seen = set()
    merged = []
    for item in seasonal + airing:
        mid = item.get('mal_id')
        if not mid or mid in seen:
            continue
        seen.add(mid)
        merged.append(item)
    return merged


# ---------------------------------------------------------------------------
# News fetch (now secondary — used only to detect hot topics)
# ---------------------------------------------------------------------------

def _clean_text(html):
    text = re.sub(r'<[^>]+>', '', html or '')
    return re.sub(r'\s+', ' ', unescape(text)).strip()


def _fetch_recent_news(max_items=20):
    try:
        feed = feedparser.parse(ANN_RSS)
        items = []
        for entry in feed.entries[:max_items]:
            title = entry.get('title', '').strip()
            if not title:
                continue
            tl = title.lower()
            if any(kw in tl for kw in EXCLUDE_NEWS_KEYWORDS):
                continue
            items.append({
                'title':   title,
                'summary': _clean_text(entry.get('summary', ''))[:280],
                'link':    entry.get('link', ''),
            })
        return items
    except Exception as e:
        print(f"[trend_picker] News fetch failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Cross-reference: does any trending anime appear in any recent headline?
# ---------------------------------------------------------------------------

def _alt_titles(anime):
    """Collect all known titles for an anime so we can match loosely."""
    titles = []
    for key in ('title', 'title_english', 'title_japanese'):
        t = anime.get(key)
        if t:
            titles.append(t)
    for entry in anime.get('titles', []) or []:
        if entry.get('title'):
            titles.append(entry['title'])
    return [t for t in titles if t]


def _find_news_match(trending, news_items):
    """Return (anime, news_item) if any trending anime appears in any headline."""
    for anime in trending:
        candidates = _alt_titles(anime)
        for cand in candidates:
            cand_lower = cand.lower()
            # Skip very short/ambiguous titles ("K", "Lupin") to avoid false positives
            if len(cand_lower) < 5:
                continue
            for item in news_items:
                text = (item['title'] + ' ' + item['summary']).lower()
                if cand_lower in text:
                    return anime, item
    return None, None


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def pick_topic():
    """Pick today's anime focus + content format."""
    print("[trend_picker] Fetching trending anime...")
    seasonal = _fetch_seasonal_top()
    time.sleep(JIKAN_DELAY)
    airing = _fetch_top_airing()
    trending = _merge_trending(seasonal, airing)

    if not trending:
        raise RuntimeError("No trending anime found — Jikan may be down")

    print(f"[trend_picker] Top 5 trending right now:")
    for i, a in enumerate(trending[:5], 1):
        title = a.get('title')
        members = a.get('members', 0)
        score = a.get('score', 0)
        print(f"  {i}. {title}  (members: {members:,}  score: {score})")

    # Try to find a news hook
    news_items = _fetch_recent_news()
    matched_anime, matched_news = _find_news_match(trending, news_items)

    if matched_anime:
        print(f"[trend_picker] News match! Anime: {matched_anime.get('title')}")
        print(f"[trend_picker]   News: {matched_news['title']}")
        return {
            'anime':        matched_anime,
            'news':         matched_news,
            'content_type': 'news_commentary',
        }

    # No news hit — pick #1 trending and rotate content type
    top_pick = trending[0]
    day = datetime.now().timetuple().tm_yday
    content_type = CONTENT_TYPES[day % len(CONTENT_TYPES)]

    print(f"[trend_picker] No news hook — using #1 trending anime")
    print(f"[trend_picker] Anime: {top_pick.get('title')}")
    print(f"[trend_picker] Content type: {content_type}")

    return {
        'anime':        top_pick,
        'news':         None,
        'content_type': content_type,
    }
