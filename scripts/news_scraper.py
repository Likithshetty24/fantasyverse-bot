import feedparser
import requests
import re

FEEDS = [
    "https://www.animenewsnetwork.com/news/rss.xml",
    "https://www.animenewsnetwork.com/all/rss.xml?ann-edition=us",
]

def clean_html(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()

def fetch_anime_news(max_items=6):
    seen_titles = set()
    news_items = []

    for feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = clean_html(entry.get('title', ''))
                summary = clean_html(entry.get('summary', entry.get('description', '')))
                link = entry.get('link', '')

                if not title or title in seen_titles:
                    continue

                # Skip reviews, encyclopedia, calendar entries — focus on news
                skip_keywords = ['encyclopedia', 'calendar', 'forum', 'review', 'interest']
                if any(kw in link.lower() for kw in skip_keywords):
                    continue

                seen_titles.add(title)
                news_items.append({
                    'title': title,
                    'summary': summary[:300] if summary else '',
                    'link': link,
                })

                if len(news_items) >= max_items:
                    break

        except Exception as e:
            print(f"[news_scraper] Failed to fetch {feed_url}: {e}")

        if len(news_items) >= max_items:
            break

    if not news_items:
        # Fallback topics if all feeds fail
        news_items = [
            {'title': 'Top Anime of the Season — What You Should Be Watching', 'summary': 'A roundup of the most talked-about anime this season.', 'link': ''},
            {'title': 'Upcoming Anime Movies in 2025 You Cannot Miss', 'summary': 'Highly anticipated anime theatrical releases coming soon.', 'link': ''},
            {'title': 'Manga to Anime Adaptations Announced This Week', 'summary': 'New anime adaptations confirmed from popular manga series.', 'link': ''},
        ]

    print(f"[news_scraper] Fetched {len(news_items)} news items")
    return news_items
