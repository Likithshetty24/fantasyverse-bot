"""
trend_picker.py
Picks today's video topic by combining "what's trending right now"
with "is there fresh news about it".

News sources (all free, no keys):
  - Anime News Network RSS  (slow but authoritative)
  - Crunchyroll News RSS    (industry-direct, often faster than ANN)
  - Reddit r/anime hot      (community-curated, fastest signal)

Strategy:
  1. Pull top ~25 currently-airing anime from Jikan
  2. Pull pooled news from 3 sources
  3. Cross-reference: trending anime with fresh news = best content
  4. Otherwise rotate through top 7 trending anime + content type rotation
"""

import re
import time
import requests
import feedparser
from html import unescape
from datetime import datetime

# ---- API / feed endpoints -----------------------------------------------
JIKAN_SEASON_NOW = "https://api.jikan.moe/v4/seasons/now"
JIKAN_TOP_AIRING = "https://api.jikan.moe/v4/top/anime"
ANN_RSS          = "https://www.animenewsnetwork.com/news/rss.xml"
CRUNCHY_RSS      = "https://www.crunchyroll.com/news/rss/anime"
REDDIT_HOT       = "https://www.reddit.com/r/anime/hot.json"

JIKAN_DELAY      = 0.4
USER_AGENT       = "FantasyVerseBot/1.0 (anime news aggregator)"

EXCLUDE_NEWS_KEYWORDS = [
    'review', 'encyclopedia', 'preview guide',
    'this week in anime', 'shelf life', 'daily streaming reviews',
]

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
# Trending anime fetch (Jikan)
# ---------------------------------------------------------------------------

def _fetch_seasonal_top():
    try:
        r = requests.get(JIKAN_SEASON_NOW,
                         params={'limit': 25, 'sfw': 'true'}, timeout=15)
        r.raise_for_status()
        items = r.json().get('data', [])
        items.sort(key=lambda x: x.get('members', 0), reverse=True)
        return items[:15]
    except Exception as e:
        print(f"[trend_picker] Seasonal top fetch failed: {e}")
        return []


def _fetch_top_airing():
    try:
        r = requests.get(JIKAN_TOP_AIRING,
                         params={'filter': 'airing', 'limit': 15}, timeout=15)
        r.raise_for_status()
        return r.json().get('data', [])
    except Exception as e:
        print(f"[trend_picker] Top airing fetch failed: {e}")
        return []


def _merge_trending(seasonal, airing):
    seen, merged = set(), []
    for item in seasonal + airing:
        mid = item.get('mal_id')
        if not mid or mid in seen:
            continue
        seen.add(mid)
        merged.append(item)
    return merged


# ---------------------------------------------------------------------------
# News fetchers (3 sources)
# ---------------------------------------------------------------------------

def _clean_text(html):
    text = re.sub(r'<[^>]+>', '', html or '')
    return re.sub(r'\s+', ' ', unescape(text)).strip()


def _is_news_worthy(title):
    tl = title.lower()
    return not any(kw in tl for kw in EXCLUDE_NEWS_KEYWORDS)


def _fetch_ann(limit=20):
    try:
        feed = feedparser.parse(ANN_RSS)
        items = []
        for entry in feed.entries[:limit]:
            title = entry.get('title', '').strip()
            if not title or not _is_news_worthy(title):
                continue
            items.append({
                'title':   title,
                'summary': _clean_text(entry.get('summary', ''))[:280],
                'link':    entry.get('link', ''),
                'source':  'ann',
            })
        return items
    except Exception as e:
        print(f"[trend_picker] ANN fetch failed: {e}")
        return []


def _fetch_crunchyroll(limit=20):
    try:
        feed = feedparser.parse(CRUNCHY_RSS)
        items = []
        for entry in feed.entries[:limit]:
            title = entry.get('title', '').strip()
            if not title or not _is_news_worthy(title):
                continue
            items.append({
                'title':   title,
                'summary': _clean_text(entry.get('summary', ''))[:280],
                'link':    entry.get('link', ''),
                'source':  'crunchyroll',
            })
        return items
    except Exception as e:
        print(f"[trend_picker] Crunchyroll fetch failed: {e}")
        return []


def _fetch_reddit(limit=25):
    try:
        r = requests.get(
            REDDIT_HOT,
            params={'limit': limit, 't': 'day'},
            headers={'User-Agent': USER_AGENT},
            timeout=15,
        )
        r.raise_for_status()
        items = []
        for child in r.json().get('data', {}).get('children', []):
            d = child.get('data', {}) or {}
            flair = (d.get('link_flair_text') or '').lower()
            # Keep only news / announcement / clip posts (community curates well)
            if not any(kw in flair for kw in ['news', 'announce', 'official', 'video']):
                continue
            title = d.get('title', '').strip()
            if not title or not _is_news_worthy(title):
                continue
            items.append({
                'title':   title,
                'summary': (d.get('selftext') or '')[:280],
                'link':    'https://reddit.com' + d.get('permalink', ''),
                'source':  'reddit',
            })
        return items
    except Exception as e:
        print(f"[trend_picker] Reddit fetch failed: {e}")
        return []


def _fetch_recent_news(max_items=40):
    """Pool news from all 3 sources, dedupe loosely by title prefix."""
    ann_items = _fetch_ann(limit=20)
    cr_items  = _fetch_crunchyroll(limit=15)
    rd_items  = _fetch_reddit(limit=25)
    print(f"[trend_picker] News sources: "
          f"ANN={len(ann_items)} Crunchyroll={len(cr_items)} Reddit={len(rd_items)}")

    pool = ann_items + cr_items + rd_items
    # Dedupe by first 35 chars of lowercase title
    seen, unique = set(), []
    for item in pool:
        key = re.sub(r'\W+', '', item['title'].lower())[:35]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    print(f"[trend_picker] Unique news items: {len(unique)}")
    return unique[:max_items]


# ---------------------------------------------------------------------------
# Cross-reference: trending anime ↔ recent headline
# ---------------------------------------------------------------------------

def _alt_titles(anime):
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
        for cand in _alt_titles(anime):
            cand_lower = cand.lower()
            if len(cand_lower) < 5:  # avoid false positives on tiny titles
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
    print("[trend_picker] Fetching trending anime from Jikan...")
    seasonal = _fetch_seasonal_top()
    time.sleep(JIKAN_DELAY)
    airing = _fetch_top_airing()
    trending = _merge_trending(seasonal, airing)

    if not trending:
        raise RuntimeError("No trending anime found — Jikan may be down")

    print(f"[trend_picker] Top 7 trending right now:")
    for i, a in enumerate(trending[:7], 1):
        title = a.get('title')
        members = a.get('members', 0)
        score = a.get('score', 0)
        print(f"  {i}. {title}  (members: {members:,}  score: {score})")

    # Pool news from ANN + Crunchyroll + Reddit
    news_items = _fetch_recent_news()
    matched_anime, matched_news = _find_news_match(trending, news_items)

    if matched_anime:
        print(f"[trend_picker] News match (source: {matched_news['source']})")
        print(f"[trend_picker]   Anime: {matched_anime.get('title')}")
        print(f"[trend_picker]   News:  {matched_news['title']}")
        return {
            'anime':        matched_anime,
            'news':         matched_news,
            'content_type': 'news_commentary',
        }

    # No news hit — ROTATE through top 7 by day-of-year so we don't post the
    # same anime multiple days in a row. Fixes "Witch Hat 4 days in a row"
    # problem and gives YouTube a clear "general anime news channel" identity.
    day = datetime.now().timetuple().tm_yday
    rotation_pool = trending[:7] if len(trending) >= 7 else trending
    slot = day % len(rotation_pool)
    top_pick = rotation_pool[slot]
    content_type = CONTENT_TYPES[day % len(CONTENT_TYPES)]

    print(f"[trend_picker] No news hook — rotating top {len(rotation_pool)}")
    print(f"[trend_picker]   Today's slot: #{slot + 1} -> {top_pick.get('title')}")
    print(f"[trend_picker]   Content type: {content_type}")

    return {
        'anime':        top_pick,
        'news':         None,
        'content_type': content_type,
    }
