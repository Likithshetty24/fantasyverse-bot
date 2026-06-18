"""
script_generator.py — Extra Time (football / World Cup)
Generates a 45-60 second football Shorts script using one of several
content formats, chosen by trend_picker.
"""

import os
import re
from groq import Groq


HUMAN_VOICE_RULES = """
WRITING STYLE — sound like a passionate football fan, NOT an AI:
- Use contractions everywhere: don't, can't, it's, they're, he's, that's
- Short, punchy sentences. Most under 13 words. Mix lengths.
- Drop natural filler: "look", "honestly", "let's be real", "here's the thing", "mate"
- Strategic ellipses ("...") for dramatic pauses before a big stat or claim
- Sound like you're at the pub arguing football with your mates, not reading a report
- NEVER say AI-narrator phrases: "In this video", "Let's dive in", "Welcome back", "Today we discuss"
- React like a fan: "what a goal", "scenes", "he cooked them", "absolute scenes", "take a bow"

RETENTION CRAFT (this is what makes views go up — follow it):
- THE HOOK IS EVERYTHING. The first sentence must stop a thumb mid-scroll.
  Lead with the single most shocking fact, number, or hot take — not a setup.
  BAD opener: "So Argentina played Algeria today and it was interesting."
  GOOD opener: "Algeria just held the World Cup champions. Nobody saw this coming."
- NEVER open with the date, the competition name, or "today". Open with the drama.
- Around the middle, drop a RETENTION TURN — a "but here's the crazy part..." /
  "and that's not even the wild bit..." pivot that makes them keep watching.
- Build to ONE debate-bait question at the end that fans CAN'T resist replying to
  (e.g. "Is this the worst result in their history, or am I overreacting?").
- CTA: give a REASON to follow tied to the moment, casual — e.g.
  "Follow so you don't miss the next World Cup shock" / "Hit follow — more reactions
  every match." Never "smash subscribe".
""".strip()


META_BLOCK_INSTRUCTIONS = """
After the script, output EXACTLY this block:

TITLE: Follow these RULES EXACTLY:
  - 45-65 characters total (counting "#Shorts" at the end)
  - Player/team/topic name in the first 30 characters
  - "#Shorts" at the END only, exactly once. NO emojis, NO all-caps spam.
  - VARY THE FORMAT every time. Do NOT use the template "[Team]'s SHOCKING [result]"
    — it's overused and kills click-through. Rotate between these patterns:
      • Question: "Did Algeria just end Argentina's reign? #Shorts"
      • Bold claim: "Messi has never looked this human #Shorts"
      • Curiosity gap: "Nobody is talking about what Mbappe just did #Shorts"
      • Number/stat: "3 records Haaland broke in one half #Shorts"
      • Callout: "Brazil fans, we need to talk about this #Shorts"
      • Hot take: "This was the worst Spain performance in years #Shorts"
  - Use a strong word but DON'T default to "SHOCKING" — rotate among:
    INSANE, UNREAL, BRUTAL, STUNNING, EMBARRASSING, GENIUS, CHAOS, DESERVED,
    ROBBED, FINISHED, GOAT, MASTERCLASS — or none if the hook is strong without it.
  BAD titles:
    ✗ "Brazil's SHOCKING draw #Shorts"   (the banned overused template)
    ✗ "Football news #Shorts"            (no specifics)
    ✗ "#Shorts Messi goal"               (Shorts at start)

DESCRIPTION: [80-120 words, passionate football-fan tone, expand on the topic,
              end with casual follow CTA]
TAGS: [15 comma-separated tags — mix broad (football, soccer, world cup, fifa, world cup 2026)
       and specific (player/team/topic names)]
THUMBNAIL_TEXT: [2-4 ALL CAPS punchy words — e.g., "MESSI GOAT", "MBAPPE UNREAL", "BIGGEST UPSET"]
BANNER_TAG: [Pick ONE: BREAKING or GOAL or WORLD CUP or STAT or LEGEND or HOT]
SEARCH_TAGS: [8 hashtags starting with #: #WorldCup2026 #Football #Soccer #FIFA etc]
""".strip()


def _prompt_debate(topic_title, topic_summary):
    return f"""You are a football debate YouTuber writing a SPICY hot-take Short for "Extra Time". This format exists to start arguments in the comments — that's the whole point. Two fanbases should be raging at each other under this video.

TODAY'S DEBATE:
{topic_title}
Angle: {topic_summary}

Pick a SIDE and commit to it hard. Be provocative, confident, a little arrogant. But back EVERY jab with a real stat or moment so it's a defensible hot take fans have to argue with — not empty trash talk.

STRUCTURE:
1. HOOK (5-8 words) — the most divisive line possible. e.g. "Ronaldo fans, this one's gonna hurt."
2. THE TAKE (10-15 sec) — state your side bluntly, then the evidence (recent games, real numbers)
3. TWIST THE KNIFE (15-40 sec) — 2-3 more points, directly compare the two sides, drop the stats
4. CLOSING (40-55 sec) — dare the other fanbase to prove you wrong + follow ask

RULES OF ENGAGEMENT (important):
- Roast the PERFORMANCE, never the human. "His movement looked finished tonight" = great.
  Mocking someone's body, family, or as a person = NEVER (gets the video pulled).
- Ground every shot in a real stat or moment so the fight is about FOOTBALL.
- End on a question fans CANNOT scroll past: "Messi or Ronaldo — settle it below."

LENGTH: 190-240 words.

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


def _prompt_news_commentary(news):
    return f"""You are a passionate football YouTuber writing the daily Shorts script for "Extra Time".

TODAY'S FOOTBALL NEWS:
Headline: {news['title']}
Context: {news['summary']}
Source: {news['source']}

Write a 45-60 second hot take on this. Informative but with real opinion and passion.

STRUCTURE:
1. HOOK (5-8 words, 0-3 sec) — bold reaction or claim
2. WHAT HAPPENED (5-15 sec) — the news in plain words
3. YOUR TAKE (15-40 sec) — 2-3 points, why it matters, what fans are saying
4. CLOSING (40-55 sec) — a verdict + a question that starts a debate. Casual follow ask.

LENGTH: 190-240 words. This is important — the video must run at least 50 seconds, so write a full, rich script. Pack in detail, specifics, and real opinion. Do not pad with filler, but do not cut it short either.

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


def _prompt_generic(topic_title, topic_summary, kind):
    framing = {
        'player_spotlight': "Break down why this player is special — skill, stats, big moments, and what they mean to their nation at the World Cup.",
        'top_moments':      "Count down or showcase the moments. Be specific — name the players, the matches, the years. Build the drama.",
        'match_hype':       "Build excitement and give a real opinion. Make predictions. Back them up with reasons fans will argue about.",
        'team_focus':       "Tell this national team's story — their stars, their history, their realistic shot at the World Cup.",
        'records_stats':    "Drop the records and numbers like trivia bombs. Make each stat land. End on the most jaw-dropping one.",
    }.get(kind, "Make it engaging, specific, and full of football passion.")

    return f"""You are a passionate football YouTuber writing the daily Shorts script for "Extra Time".

TODAY'S TOPIC:
{topic_title}
Context: {topic_summary}

{framing}

STRUCTURE:
1. HOOK (5-8 words, 0-3 sec) — bold claim or curiosity gap
2. SETUP (5-15 sec) — frame the topic
3. THE GOODS (15-40 sec) — 2-3 specific beats: players, stats, moments, with real opinion
4. CLOSING (40-55 sec) — a verdict + a debate-starting question. Casual follow ask.

LENGTH: 190-240 words. This is important — the video must run at least 50 seconds, so write a full, rich script. Pack in detail, specifics, and real opinion. Do not pad with filler, but do not cut it short either.

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF"
    "]+",
    flags=re.UNICODE,
)


def _polish_title(raw_title, subject=''):
    t = raw_title.strip().strip('"\'')
    t = _EMOJI_RE.sub('', t)
    t = re.sub(r'#\s*[Ss]horts?', '', t)
    t = re.sub(r'!{2,}', '!', t)
    t = re.sub(r'\?{2,}', '?', t)
    t = re.sub(r'\s+', ' ', t).strip(' -–—:|')

    if subject and subject.lower() not in t.lower():
        t = f"{subject}: {t}"

    suffix = " #Shorts"
    max_body = 65 - len(suffix)
    if len(t) > max_body:
        t = t[:max_body].rstrip(' .,;:!-–—')
    return f"{t}{suffix}"


def _prompt_match_news(match, phase):
    """phase = 'HALF-TIME' or 'FULL-TIME'."""
    home = match['home']
    away = match['away']
    hs   = match['home_score']
    as_  = match['away_score']
    events = match.get('events_text', '')
    return f"""You are a passionate football YouTuber writing an instant {phase} reaction Short for "Fantasy Verse".

MATCH: {home} {hs} - {as_} {away}  ({phase})
{('Key events: ' + events) if events else ''}

Write a 50-60 second {phase} reaction. This is a NEWS reaction video — fast, current, opinionated. Lean into talking points and controversy (refereeing calls, big misses, tactical decisions, standout or underperforming players) the way football Twitter does after a match.

STRUCTURE:
1. HOOK (5-8 words) — the headline of this {phase.lower()}
2. THE SCORE & STORY (10-15 sec) — what's happened so far / final result
3. TALKING POINTS (20-35 sec) — 2-3 things people are arguing about. Controversy, standout players, what went wrong/right
4. CLOSING (45-55 sec) — your verdict / what to watch {'in the second half' if phase == 'HALF-TIME' else 'next'} + a debate-starting question. Casual follow ask.

LENGTH: 190-240 words (video must be at least 50 seconds).

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


def generate_match_news(match, phase):
    """
    Generate a HT/FT reaction video's script + metadata.
    match dict: home, away, home_score, away_score, events_text (optional)
    phase: 'HALF-TIME' or 'FULL-TIME'
    """
    client = Groq(api_key=os.environ['GROQ_API_KEY'])
    prompt = _prompt_match_news(match, phase)

    print(f"[script_generator] Match news: {match['home']} vs {match['away']} ({phase})")

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.85,
        max_tokens=1800,
    )
    raw = response.choices[0].message.content

    def extract(label):
        pattern = rf'^{label}:\s*(.+?)(?=\n[A-Z_]+:|$)'
        m = re.search(pattern, raw, re.MULTILINE | re.DOTALL)
        return m.group(1).strip() if m else ''

    script = re.split(r'\nTITLE:', raw, maxsplit=1)[0].strip()

    subject = f"{match['home']} vs {match['away']}"
    title = _polish_title(extract('TITLE'), '')
    description = extract('DESCRIPTION')
    tags = [t.strip() for t in extract('TAGS').split(',') if t.strip()]
    thumbnail_text = extract('THUMBNAIL_TEXT') or f"{match['home_score']}-{match['away_score']}"
    banner_tag = (extract('BANNER_TAG') or
                  ('HALF TIME' if phase == 'HALF-TIME' else 'FULL TIME')).upper().strip()
    search_tags = extract('SEARCH_TAGS')

    return {
        'script':         script,
        'title':          title,
        'description':    f"{description}\n\n{search_tags}",
        'tags':           tags,
        'thumbnail_text': thumbnail_text,
        'banner_tag':     banner_tag,
        # two real subjects for footage = both teams
        'image_subject':  [match['home'], match['away']],
        'content_type':   'match_news',
    }


def generate_script_and_metadata(topic):
    client = Groq(api_key=os.environ['GROQ_API_KEY'])
    content_type = topic.get('content_type', 'player_spotlight')

    if content_type == 'news_commentary':
        prompt = _prompt_news_commentary(topic['news'])
    elif content_type == 'debate':
        prompt = _prompt_debate(topic['topic_title'], topic['topic_summary'])
    else:
        prompt = _prompt_generic(topic['topic_title'], topic['topic_summary'], content_type)

    print(f"[script_generator] Content type: {content_type}")
    print(f"[script_generator] Topic: {topic.get('topic_title', '<news>')}")

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.85,
        max_tokens=1800,
    )

    raw = response.choices[0].message.content

    def extract(label):
        pattern = rf'^{label}:\s*(.+?)(?=\n[A-Z_]+:|$)'
        match   = re.search(pattern, raw, re.MULTILINE | re.DOTALL)
        return match.group(1).strip() if match else ''

    script_match = re.split(r'\nTITLE:', raw, maxsplit=1)
    script       = script_match[0].strip()

    subject        = topic.get('image_subject', '')
    title          = _polish_title(extract('TITLE'), subject)
    description    = extract('DESCRIPTION')
    tags_raw       = extract('TAGS')
    tags           = [t.strip() for t in tags_raw.split(',') if t.strip()]
    thumbnail_text = extract('THUMBNAIL_TEXT')
    _default_banner = {'news_commentary': 'BREAKING', 'debate': 'HOT TAKE'}.get(
        content_type, 'WORLD CUP')
    banner_tag     = (extract('BANNER_TAG') or _default_banner).upper().strip()
    search_tags    = extract('SEARCH_TAGS')

    full_description = f"{description}\n\n{search_tags}"

    print(f"[script_generator] Script: {len(script.split())} words")
    print(f"[script_generator] Title: {title}")
    print(f"[script_generator] Banner: {banner_tag}")

    return {
        'script':         script,
        'title':          title,
        'description':    full_description,
        'tags':           tags,
        'thumbnail_text': thumbnail_text,
        'banner_tag':     banner_tag,
        'image_subject':  subject,
        'content_type':   content_type,
    }
