"""
script_generator.py
Generates the Short script using one of 7 content formats, chosen by
trend_picker based on what's trending and whether news exists.

Each format has its own prompt so the script structure matches the
content type — a "top 5 moments" script is paced differently from
a "news commentary" script.
"""

import os
import re
from groq import Groq
from datetime import datetime


HUMAN_VOICE_RULES = """
WRITING STYLE — sound like a real person, NOT an AI:
- Use contractions everywhere: don't, can't, it's, they're, you'd, gonna, kinda
- Short, punchy sentences. Most under 12 words. Mix sentence lengths.
- Drop natural filler occasionally: "okay so", "look", "honestly", "like", "basically", "wait"
- Strategic ellipses ("...") for natural pauses at tension moments
- Sound like you're texting a friend who's also an anime fan, not reading a press release
- Personal hooks: "I just saw this and...", "Bro, you're not ready", "Wait till you hear this"
- NEVER say robotic phrases: "It has been announced", "We are excited to share", "In other news"
- Replace marketing-speak: "smash subscribe" → "hit follow" / "tap subscribe" / "don't sleep on this channel"
- React like a fan, not a reporter: "yo", "no way", "I'm dead", "this hits different"
""".strip()


META_BLOCK_INSTRUCTIONS = """
After the script, output EXACTLY this block:

TITLE: Follow these RULES EXACTLY:
  - 45-65 characters total (counting "#Shorts" at the end)
  - Format: [ANIME NAME] [hook claim or reaction] #Shorts
  - Anime name MUST appear in the first 30 characters
  - MUST include exactly one power word: HUGE, MASSIVE, SHOCKING, INSANE, BROKEN, COOKED, CRAZY, WILD, NUTS
  - "#Shorts" goes ONLY at the end, never at the start, exactly once
  - NO emojis, NO multiple consecutive caps words, NO clickbait punctuation spam
  GOOD examples (copy this style):
    ✓ "Jujutsu Kaisen just dropped a MASSIVE Season 3 update #Shorts"
    ✓ "Solo Leveling fans are losing it over this leak #Shorts"
    ✓ "My Hero Academia's ending is BROKEN — here's why #Shorts"
    ✓ "Demon Slayer Season 5 announcement is INSANE #Shorts"
  BAD examples (NEVER do this):
    ✗ "JJK #Shorts"                          (no hook, too short)
    ✗ "#Shorts Anime News Today"             (Shorts at start, no anime)
    ✗ "Witch Hat 🔥🔥 #Shorts"               (emojis)
    ✗ "BREAKING HUGE MASSIVE NEWS!!! #Shorts" (clickbait spam)

DESCRIPTION: [80-120 words, casual tone matching the script, end with casual follow CTA]
TAGS: [15 comma-separated tags, mix broad (anime, manga, otaku, anime 2026) and specific anime/character names]
THUMBNAIL_TEXT: [2-4 ALL CAPS punchy words — e.g., "JJK SHOCKER", "MHA COOKED"]
BANNER_TAG: [Pick ONE: BREAKING or LEAKED or HUGE or RUMOR or TRENDING]
FOCUS_CHARACTERS: [Up to 4 comma-separated character names mentioned in the script. Empty if none.]
SEARCH_TAGS: [8 hashtags starting with #]
""".strip()


# Emoji + clickbait spam stripper
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport
    "\U0001F700-\U0001F77F"  # alchemical
    "\U0001F900-\U0001F9FF"  # supplemental
    "\U0001FA00-\U0001FA6F"  # extended-A
    "\U0001FA70-\U0001FAFF"  # extended-B
    "\U00002600-\U000026FF"  # misc symbols
    "\U00002700-\U000027BF"  # dingbats
    "]+",
    flags=re.UNICODE,
)

POWER_WORDS = ['HUGE', 'MASSIVE', 'SHOCKING', 'INSANE', 'BROKEN',
               'COOKED', 'CRAZY', 'WILD', 'NUTS']


def _polish_title(raw_title, anime_name):
    """Clean up Groq's title and enforce our rules. Returns final title."""
    t = raw_title.strip()

    # 1. Strip any quotation marks
    t = t.strip('"\'')

    # 2. Strip emojis
    t = _EMOJI_RE.sub('', t)

    # 3. Strip all #Shorts mentions (we re-add one at end)
    t = re.sub(r'#\s*[Ss]horts?', '', t)

    # 4. Collapse repeated punctuation/whitespace
    t = re.sub(r'!{2,}', '!', t)
    t = re.sub(r'\?{2,}', '?', t)
    t = re.sub(r'\s+', ' ', t).strip(' -–—:|')

    # 5. If anime name isn't in title, prepend it
    if anime_name and anime_name.lower() not in t.lower():
        t = f"{anime_name} {t}"

    # 6. Truncate body so " #Shorts" fits within 65 chars
    suffix = " #Shorts"
    max_body = 65 - len(suffix)
    if len(t) > max_body:
        t = t[:max_body].rstrip(' .,;:!-–—')

    # 7. If we still have no power word, log warning (don't force-insert
    #    -- would read awkwardly; better to let Groq's title pass through)
    has_power = any(w in t.upper() for w in POWER_WORDS)
    if not has_power:
        print(f"[script_generator] WARNING: title missing power word: {t!r}")

    return f"{t}{suffix}"


# ---------------------------------------------------------------------------
# Per-format prompts
# ---------------------------------------------------------------------------

def _prompt_news_commentary(anime_title, synopsis, news):
    return f"""You are a 23-year-old anime YouTuber doing the daily Shorts script for "Fantasy Verse".

TODAY'S STORY:
Anime: {anime_title} (one of the most-watched anime right now)
Quick context: {synopsis}
Recent news: {news['title']}
News details: {news['summary']}

Write a 30-50 second high-energy reaction video about this news.

STRUCTURE:
1. HOOK (5-8 words, 0-3 sec) — shocked reaction or hot take
2. THE NEWS (5-15 sec) — what happened, one or two short sentences
3. REACTION + DETAILS (15-40 sec) — your take, fan reactions, what it means
4. CLOSING (40-50 sec) — the "so what" + a real question to drive comments

LENGTH: 120-160 words (this gives ~50-65 second runtime — Shorts retention sweet spot).

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


def _prompt_character_spotlight(anime_title, synopsis):
    return f"""You are a 23-year-old anime YouTuber making a character spotlight Short for "Fantasy Verse".

TODAY'S ANIME (currently trending, one of the most-watched right now):
{anime_title}
Quick context: {synopsis}

Pick ONE iconic character from this anime and break down why they're elite — power, personality, character arc, or a single legendary moment.

STRUCTURE:
1. HOOK (5-8 words) — bold claim about the character ("Gojo Satoru is anime's most overpowered character. Here's why.")
2. WHO THEY ARE (5-15 sec) — quick intro
3. WHY THEY'RE ELITE (15-40 sec) — 2-3 specific reasons with examples
4. CLOSING (40-50 sec) — your hot take + ask viewers for their pick

LENGTH: 120-160 words (this gives ~50-65 second runtime — Shorts retention sweet spot).

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


def _prompt_top_moments(anime_title, synopsis):
    return f"""You are a 23-year-old anime YouTuber making a "Top 3 Moments" Short for "Fantasy Verse".

TODAY'S ANIME (currently trending):
{anime_title}
Quick context: {synopsis}

Pick the TOP 3 most shocking, hype, or emotional moments from this anime and rank them. Be specific with episode references where possible.

STRUCTURE:
1. HOOK (5-8 words) — "These 3 moments broke anime Twitter."
2. NUMBER 3 (8 sec) — set up briefly, then the moment, your reaction
3. NUMBER 2 (8 sec) — same pattern
4. NUMBER 1 (12 sec) — bigger build, the moment, why it's #1
5. CLOSING (5 sec) — ask viewers what they'd put at #1

LENGTH: 130-170 words (this gives ~55-70 second runtime — Shorts retention sweet spot).

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


def _prompt_power_scaling(anime_title, synopsis):
    return f"""You are a 23-year-old anime YouTuber making a power-scaling debate Short for "Fantasy Verse".

TODAY'S ANIME (currently trending):
{anime_title}
Quick context: {synopsis}

Set up a fan-favorite "who would win" matchup involving a character from this anime vs another iconic anime character. Argue ONE side with conviction, then ask viewers.

STRUCTURE:
1. HOOK (5-8 words) — "Most fans get this matchup wrong."
2. THE MATCHUP (5-10 sec) — set it up: "[Character A] vs [Character B]"
3. THE ARGUMENT (15-35 sec) — 2-3 reasons why your pick wins
4. CLOSING (40-50 sec) — concede one weakness for credibility, then ask "Who wins?"

LENGTH: 125-165 words (this gives ~55-65 second runtime — Shorts retention sweet spot).

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


def _prompt_lore_drop(anime_title, synopsis):
    return f"""You are a 23-year-old anime YouTuber making a lore-deep-dive Short for "Fantasy Verse".

TODAY'S ANIME (currently trending):
{anime_title}
Quick context: {synopsis}

Reveal ONE piece of lore, theory, or hidden detail that casual viewers usually miss. Could be foreshadowing, a name meaning, a Japanese cultural reference, a hidden manga panel detail, or a fan theory with real evidence.

STRUCTURE:
1. HOOK (5-8 words) — "Most fans missed this detail in [anime]."
2. SETUP (5-10 sec) — what you're about to reveal
3. THE REVEAL (15-35 sec) — the detail itself + the evidence
4. CLOSING (40-50 sec) — what it means for the story + ask if viewers caught it

LENGTH: 125-165 words (this gives ~55-65 second runtime — Shorts retention sweet spot).

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


def _prompt_manga_vs_anime(anime_title, synopsis):
    return f"""You are a 23-year-old anime YouTuber making a "manga vs anime" comparison Short for "Fantasy Verse".

TODAY'S ANIME (currently trending):
{anime_title}
Quick context: {synopsis}

Reveal 2-3 things the anime CHANGED or CUT from the manga. Be specific where possible. Take a clear stance on whether the anime did it better or the manga.

STRUCTURE:
1. HOOK (5-8 words) — "The anime butchered this manga scene."
2. CHANGE #1 (10 sec) — what was changed
3. CHANGE #2 (10 sec) — what was changed
4. (optional) CHANGE #3 (10 sec)
5. CLOSING (5-10 sec) — your verdict + ask viewers which version they prefer

LENGTH: 125-165 words (this gives ~55-65 second runtime — Shorts retention sweet spot).

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


def _prompt_why_trending(anime_title, synopsis):
    return f"""You are a 23-year-old anime YouTuber making a "why everyone is watching this" Short for "Fantasy Verse".

TODAY'S ANIME (currently the most-watched anime — viral right now):
{anime_title}
Quick context: {synopsis}

Explain in fan-friendly terms why this anime is blowing up RIGHT NOW. Animation quality? Story twist? Character moment? Viral scene? Pick 2-3 concrete reasons.

STRUCTURE:
1. HOOK (5-8 words) — "If you're not watching [anime] yet, fix that."
2. THE PITCH (5-15 sec) — quick what-it's-about for newcomers
3. WHY IT'S HOT (15-40 sec) — 2-3 specific reasons it's trending
4. CLOSING (40-50 sec) — where to start watching + ask if viewers are caught up

LENGTH: 125-165 words (this gives ~55-65 second runtime — Shorts retention sweet spot).

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


PROMPT_DISPATCH = {
    'news_commentary':     _prompt_news_commentary,
    'character_spotlight': _prompt_character_spotlight,
    'top_moments':         _prompt_top_moments,
    'power_scaling':       _prompt_power_scaling,
    'lore_drop':           _prompt_lore_drop,
    'manga_vs_anime':      _prompt_manga_vs_anime,
    'why_trending':        _prompt_why_trending,
}


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def generate_script_and_metadata(topic):
    """
    Args:
        topic = {'anime': {...mal entry...}, 'news': {...}|None, 'content_type': str}
    """
    client = Groq(api_key=os.environ['GROQ_API_KEY'])

    anime       = topic['anime']
    news        = topic.get('news')
    content_type = topic.get('content_type', 'why_trending')

    anime_title = anime.get('title_english') or anime.get('title') or 'Anime'
    synopsis    = (anime.get('synopsis') or '')[:600]

    builder = PROMPT_DISPATCH.get(content_type, _prompt_why_trending)

    if content_type == 'news_commentary':
        prompt = builder(anime_title, synopsis, news)
    else:
        prompt = builder(anime_title, synopsis)

    print(f"[script_generator] Content type: {content_type}")
    print(f"[script_generator] Anime: {anime_title}")

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.9,
        max_tokens=1600,
    )

    raw = response.choices[0].message.content

    def extract(label):
        pattern = rf'^{label}:\s*(.+?)(?=\n[A-Z_]+:|$)'
        match   = re.search(pattern, raw, re.MULTILINE | re.DOTALL)
        return match.group(1).strip() if match else ''

    script_match = re.split(r'\nTITLE:', raw, maxsplit=1)
    script       = script_match[0].strip()

    title          = extract('TITLE')
    description    = extract('DESCRIPTION')
    tags_raw       = extract('TAGS')
    tags           = [t.strip() for t in tags_raw.split(',') if t.strip()]
    thumbnail_text = extract('THUMBNAIL_TEXT')
    banner_tag     = extract('BANNER_TAG') or ('BREAKING' if content_type == 'news_commentary' else 'TRENDING')
    focus_chars_raw = extract('FOCUS_CHARACTERS')
    focus_characters = [c.strip() for c in focus_chars_raw.split(',') if c.strip()]
    search_tags    = extract('SEARCH_TAGS')

    # Strict title polish: strip emojis/junk, ensure anime name first,
    # truncate to 65 chars + " #Shorts" at end exactly once.
    title = _polish_title(title, anime_title)

    full_description = f"{description}\n\n{search_tags}"

    print(f"[script_generator] Script: {len(script.split())} words")
    print(f"[script_generator] Title: {title}")
    print(f"[script_generator] Banner: {banner_tag}")
    if focus_characters:
        print(f"[script_generator] Characters: {', '.join(focus_characters)}")

    return {
        'script':           script,
        'title':            title,
        'description':      full_description,
        'tags':             tags,
        'thumbnail_text':   thumbnail_text,
        'banner_tag':       banner_tag.upper().strip(),
        'focus_anime':      anime_title,
        'focus_characters': focus_characters,
        'content_type':     content_type,
    }
