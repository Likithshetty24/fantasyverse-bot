"""
news_scraper.py
Pulls trending anime news from Anime News Network RSS.
Filters out reviews and encyclopedia entries — only real news items.
"""

import feedparser
import re
from html import unescape

ANN_RSS = "https://www.animenewsnetwork.com/news/rss.xml"

# Skip these — they're not news
EXCLUDE_KEYWORDS = [
    'review',
    'encyclopedia',
    'preview guide',
    'this week in anime',
    'shelf life',
]


def _clean_summary(html):
    """Strip HTML, collapse whitespace, truncate to ~280 chars."""
    text = re.sub(r'<[^>]+>', '', html)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:280]


def fetch_anime_news(max_items=5):
    """Return list of top news items: [{'title','summary','link'}, ...]."""
    print(f"[news_scraper] Fetching from ANN RSS...")
    feed = feedparser.parse(ANN_RSS)

    items = []
    for entry in feed.entries:
        title = entry.get('title', '').strip()
        if not title:
            continue
        title_lower = title.lower()
        if any(kw in title_lower for kw in EXCLUDE_KEYWORDS):
            continue

        summary = _clean_summary(entry.get('summary', ''))
        link    = entry.get('link', '')

        items.append({'title': title, 'summary': summary, 'link': link})
        if len(items) >= max_items:
            break

    print(f"[news_scraper] Got {len(items)} news items")
    return items
