"""
trend_picker.py — Extra Time (football / FIFA World Cup)
Picks today's football topic by combining live buzz with a curated pool.

News sources (all free):
  - Reddit r/soccer hot       (fastest community buzz)
  - BBC Sport football RSS    (authoritative headlines)
  - The Guardian football RSS (authoritative headlines)

Content types:
  - news_commentary    when fresh football news is hot
  - player_spotlight   star players (World Cup focus)
  - top_moments        greatest goals / matches / moments
  - team_focus         national teams + their World Cup story
  - records_stats      "did you know" records and numbers
  - match_hype         World Cup 2026 fixtures / predictions
"""

import re
import random
import requests
import feedparser
from html import unescape
from datetime import datetime

REDDIT_SOCCER = "https://www.reddit.com/r/soccer/hot.json"
BBC_RSS       = "https://feeds.bbci.co.uk/sport/football/rss.xml"
GUARDIAN_RSS  = "https://www.theguardian.com/football/rss"

USER_AGENT    = "ExtraTimeBot/1.0 (football shorts aggregator)"

EXCLUDE_NEWS_KEYWORDS = ['quiz', 'crossword', 'podcast', 'how to watch', 'tv guide']


CONTENT_TYPES = [
    'debate',           # weighted heaviest — biggest comment driver
    'player_spotlight',
    'debate',
    'top_moments',
    'match_hype',
    'debate',
    'team_focus',
    'records_stats',
]


# ---------------------------------------------------------------------------
# Curated topic pool — heavily World Cup 2026 focused, football-general overall
# Each entry: (content_type, title, summary, image_subject)
#   image_subject -> a player or team name we can look up real images for,
#                    or '' for a generic football aesthetic
# ---------------------------------------------------------------------------

CURATED_TOPICS = [
    # ---- Debate / hot-take (engagement gold — Messi vs Ronaldo etc.) ----
    ('debate', 'Messi vs Ronaldo — is the debate finally over?',
     'Messi still scoring hat-tricks at 38 while Ronaldo struggles for form. Argue the GOAT debate is settled.', 'Lionel Messi'),
    ('debate', 'Is Cristiano Ronaldo finished at this World Cup?',
     'Ronaldo poor performances and low ratings. Make the case he is past it — back it with stats, not insults.', 'Cristiano Ronaldo'),
    ('debate', 'Messi is STILL the GOAT at 38',
     'Messi defying age. Defend the GOAT claim with his World Cup numbers.', 'Lionel Messi'),
    ('debate', 'The most overrated player at the 2026 World Cup',
     'Pick a big name not living up to the hype and make the case.', ''),
    ('debate', 'Mbappe vs Haaland — who is the real next GOAT?',
     'The heir-to-the-throne debate. Pick a side and commit.', 'Kylian Mbappe'),
    ('debate', 'Vinicius or Lamine Yamal — who is better right now?',
     'The best-young-winger debate that splits fans.', 'Vinicius Junior'),
    ('debate', 'Is this the worst Brazil side in history?',
     'Brazil underperforming again. Argue whether the Selecao have fallen off.', 'Brazil'),
    ('debate', 'England are frauds until they prove otherwise',
     'England talent vs trophies. Make the spicy case.', 'England'),

    # ---- Star player spotlights ----
    ('player_spotlight', 'Lionel Messi at the 2026 World Cup',
     'the GOAT debate, his final World Cup, and what Argentina needs from him', 'Lionel Messi'),
    ('player_spotlight', 'Kylian Mbappe',
     'the fastest man in football and France\'s talisman chasing a second World Cup', 'Kylian Mbappe'),
    ('player_spotlight', 'Erling Haaland',
     'the goal machine and why Norway missing the World Cup is football\'s biggest what-if', 'Erling Haaland'),
    ('player_spotlight', 'Jude Bellingham',
     'England\'s golden boy and the midfielder carrying a nation\'s hopes', 'Jude Bellingham'),
    ('player_spotlight', 'Vinicius Junior',
     'Brazil\'s electric winger and the favourite for the Golden Ball', 'Vinicius Junior'),
    ('player_spotlight', 'Lamine Yamal',
     'the teenage sensation lighting up world football for Spain', 'Lamine Yamal'),
    ('player_spotlight', 'Cristiano Ronaldo',
     'the legend\'s last dance and whether Portugal can send him out a champion', 'Cristiano Ronaldo'),
    ('player_spotlight', 'Rodri',
     'the Ballon d\'Or winning anchor that makes Spain tick', 'Rodri'),

    # ---- Top moments ----
    ('top_moments', 'Greatest World Cup goals ever',
     'from Maradona\'s solo run to Messi\'s magic — the goals that defined the tournament', ''),
    ('top_moments', 'Most shocking World Cup upsets',
     'Saudi Arabia beating Argentina, Germany crashing out — football\'s biggest shocks', ''),
    ('top_moments', 'Greatest World Cup finals',
     'the most dramatic finals in history and what made them unforgettable', ''),
    ('top_moments', 'Iconic World Cup celebrations',
     'the celebrations that became legendary moments in football history', ''),
    ('top_moments', 'Best World Cup saves ever',
     'Gordon Banks to the modern era — keepers who defied physics', ''),

    # ---- Match hype / World Cup 2026 ----
    ('match_hype', 'World Cup 2026 favourites',
     'Argentina, France, Brazil, Spain, England — who actually wins it', ''),
    ('match_hype', 'World Cup 2026 dark horses',
     'the nations nobody is talking about that could go far', ''),
    ('match_hype', 'The biggest World Cup 2026 group stage clashes',
     'the must-watch fixtures of the group stage', ''),
    ('match_hype', 'Why the 2026 World Cup is the biggest ever',
     '48 teams, 3 host nations, 104 matches — everything that changed', ''),
    ('match_hype', 'World Cup 2026 Golden Boot race',
     'the strikers most likely to finish top scorer', ''),

    # ---- Team focus ----
    ('team_focus', 'Argentina at the 2026 World Cup',
     'the defending champions and whether they can go back to back', 'Argentina'),
    ('team_focus', 'France national team',
     'arguably the deepest squad in the world and the team to beat', 'France'),
    ('team_focus', 'Brazil national team',
     'five-time champions desperate to end a 24-year wait', 'Brazil'),
    ('team_focus', 'England national team',
     'football\'s nearly-men and whether this is finally their year', 'England'),
    ('team_focus', 'Spain national team',
     'the Euro champions playing the best football on the planet', 'Spain'),
    ('team_focus', 'Germany national team',
     'the four-time winners rebuilding after back-to-back group exits', 'Germany'),

    # ---- Records & stats ----
    ('records_stats', 'Most World Cup goals of all time',
     'Klose, Ronaldo, Muller — the all-time top scorers and who can catch them', ''),
    ('records_stats', 'Players with the most World Cup appearances',
     'the iron men who kept showing up tournament after tournament', ''),
    ('records_stats', 'Youngest and oldest World Cup scorers',
     'the record-breakers at both ends of the age scale', ''),
    ('records_stats', 'Countries that have won the most World Cups',
     'Brazil leads with five — the full ranking and the nearly men', ''),
    ('records_stats', 'Fastest goals in World Cup history',
     'the strikes that beat the clock within seconds of kickoff', ''),
]


# ---------------------------------------------------------------------------
# News fetchers
# ---------------------------------------------------------------------------

def _clean_text(html):
    text = re.sub(r'<[^>]+>', '', html or '')
    return re.sub(r'\s+', ' ', unescape(text)).strip()


def _is_news_worthy(title):
    tl = title.lower()
    return not any(kw in tl for kw in EXCLUDE_NEWS_KEYWORDS)


def _fetch_reddit(limit=20):
    try:
        r = requests.get(REDDIT_SOCCER, params={'limit': limit, 't': 'day'},
                         headers={'User-Agent': USER_AGENT}, timeout=15)
        r.raise_for_status()
        items = []
        for child in r.json().get('data', {}).get('children', []):
            d = child.get('data', {}) or {}
            flair = (d.get('link_flair_text') or '').lower()
            title = (d.get('title') or '').strip()
            if not title or not _is_news_worthy(title):
                continue
            # Best-effort current image from the post preview
            img_url = ''
            prev = d.get('preview', {})
            if isinstance(prev, dict) and prev.get('images'):
                img_url = (prev['images'][0].get('source', {}) or {}).get('url', '')
            # r/soccer flairs: News, Media, Stats, Transfers, Discussion, etc.
            items.append({
                'title':     title,
                'summary':   (d.get('selftext') or '')[:280],
                'link':      'https://reddit.com' + d.get('permalink', ''),
                'source':    'reddit',
                'flair':     flair,
                'image_url': img_url,
            })
        return items
    except Exception as e:
        print(f"[trend_picker] Reddit fetch failed: {e}")
        return []


def _fetch_rss(url, source_name, limit=15):
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:limit]:
            title = entry.get('title', '').strip()
            if not title or not _is_news_worthy(title):
                continue
            items.append({
                'title':   title,
                'summary': _clean_text(entry.get('summary', ''))[:280],
                'link':    entry.get('link', ''),
                'source':  source_name,
                'flair':   '',
            })
        return items
    except Exception as e:
        print(f"[trend_picker] {source_name} RSS failed: {e}")
        return []


def _fetch_all_news():
    pool = []
    pool += _fetch_reddit(limit=20)
    pool += _fetch_rss(BBC_RSS, 'bbc', limit=15)
    pool += _fetch_rss(GUARDIAN_RSS, 'guardian', limit=15)

    by_source = {}
    for item in pool:
        by_source[item['source']] = by_source.get(item['source'], 0) + 1
    print(f"[trend_picker] News sources: " +
          ", ".join(f"{k}={v}" for k, v in by_source.items()))

    seen, unique = set(), []
    for item in pool:
        key = re.sub(r'\W+', '', item['title'].lower())[:40]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


# ---------------------------------------------------------------------------
# Score news relevance — World Cup + big names rank higher
# ---------------------------------------------------------------------------

HOT_KEYWORDS = [
    'world cup', 'fifa', 'messi', 'mbappe', 'mbappé', 'haaland', 'ronaldo',
    'bellingham', 'vinicius', 'vinícius', 'yamal', 'argentina', 'france',
    'brazil', 'england', 'spain', 'germany', 'portugal', 'goal', 'hat-trick',
    'hat trick', 'final', 'semfinal', 'semi-final', 'knockout', 'group stage',
    'golden boot', 'wins', 'beat', 'stunner', 'comeback', 'penalty',
]


def _score_news_item(item):
    text = (item['title'] + ' ' + item['summary']).lower()
    score = sum(1 for kw in HOT_KEYWORDS if kw in text)
    if 'world cup' in text or 'fifa' in text:
        score += 4  # strongly prefer World Cup news while tournament is live
    flair = item.get('flair', '')
    if any(f in flair for f in ['news', 'media', 'official']):
        score += 1
    if item['source'] in ('bbc', 'guardian'):
        score += 1
    return score


def _extract_image_subject(text):
    """Try to pull a player or team name from a headline for image lookup."""
    known = ['Lionel Messi', 'Messi', 'Kylian Mbappe', 'Mbappe', 'Erling Haaland',
             'Haaland', 'Cristiano Ronaldo', 'Ronaldo', 'Jude Bellingham', 'Bellingham',
             'Vinicius Junior', 'Vinicius', 'Lamine Yamal', 'Yamal', 'Rodri',
             'Argentina', 'France', 'Brazil', 'England', 'Spain', 'Germany',
             'Portugal', 'Netherlands', 'Italy', 'Croatia']
    for name in known:
        if name.lower() in text.lower():
            return name
    return ''


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def pick_topic():
    today = datetime.now()
    day_of_year = today.timetuple().tm_yday

    print("[trend_picker] Fetching football news...")
    news_items = _fetch_all_news()
    print(f"[trend_picker] Unique items: {len(news_items)}")

    scored = [(item, _score_news_item(item)) for item in news_items]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Strong news (a real World Cup / big-name story) wins the day
    if scored and scored[0][1] >= 4:
        best, sc = scored[0]
        subject = _extract_image_subject(best['title'] + ' ' + best['summary'])
        print(f"[trend_picker] News-driven topic (score {sc}, {best['source']})")
        print(f"[trend_picker]   {best['title']}")
        return {
            'content_type':  'news_commentary',
            'news':          best,
            'topic_title':   best['title'],
            'topic_summary': best['summary'],
            'image_subject': subject,
            'rng_seed':      today.strftime('%Y%m%d'),
        }

    # Otherwise rotate the curated pool by content type + day
    content_type = CONTENT_TYPES[day_of_year % len(CONTENT_TYPES)]
    matching = [t for t in CURATED_TOPICS if t[0] == content_type] or CURATED_TOPICS
    ct, title, summary, subject = matching[day_of_year % len(matching)]

    print(f"[trend_picker] Curated rotation -> {ct}")
    print(f"[trend_picker]   Topic: {title}")

    return {
        'content_type':  ct,
        'news':          None,
        'topic_title':   title,
        'topic_summary': summary,
        'image_subject': subject,
        'rng_seed':      today.strftime('%Y%m%d'),
    }
