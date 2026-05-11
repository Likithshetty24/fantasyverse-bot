"""
script_generator.py
Director-style anime news Shorts script for Fantasy Verse.
Output is a tight 30-60 sec script structured into HOOK / CONTEXT / REVEAL / PAYOFF
beats so the video assembler can map each section to a visual shot.
"""

import os
import re
from groq import Groq
from datetime import datetime


def generate_script_and_metadata(news_items):
    client = Groq(api_key=os.environ['GROQ_API_KEY'])

    news_block = '\n'.join(
        f"{i+1}. {item['title']}\n   {item['summary']}"
        for i, item in enumerate(news_items)
    )

    today = datetime.now().strftime('%B %d, %Y')

    prompt = f"""You are a viral YouTube Shorts director writing for an anime news channel called Fantasy Verse.

Today is {today}. Pick the SINGLE most exciting story from this news feed and write a high-energy 30-60 second Short script:

{news_block}

SCRIPT STRUCTURE (write as flowing narration, no labels in output):

[HOOK - first 6 words, 0-3 sec]
A punchy 5-8 word opening line that creates shock or curiosity. Examples:
- "This changes EVERYTHING for One Piece."
- "Fans are losing it right now."
- "No one saw this coming."

[CONTEXT - 3-10 sec]
One sentence stating what the news is.

[REVEAL - 10-40 sec]
2-3 micro-beats, each 1-2 short sentences. Build excitement. Use fan reactions.

[PAYOFF + CTA - 40-55 sec]
Deliver the "so what" — why this matters. End with a question to drive comments:
"Is this a W or L?" / "Who's hyped?" / "What do you think?"
Then close with: "Smash subscribe to Fantasy Verse for daily anime news!"

CRITICAL RULES:
- Total length: 80-130 words (reads in 30-55 seconds at ~170 wpm pace)
- High energy, fast-paced — every sentence punches
- NO section headers, NO stage directions, NO sound effect labels — pure spoken narration
- Use power words: HUGE, SHOCKING, INSANE, MASSIVE, BROKEN
- Mark rumors clearly with "rumored" or "unconfirmed"

After the script, output EXACTLY this block:
TITLE: [YouTube title, max 70 chars, MUST include #Shorts, year 2026, power word like SHOCKING or HUGE]
DESCRIPTION: [80-120 word description, include keywords naturally, end with subscribe CTA]
TAGS: [15 comma-separated tags — mix broad (anime, manga, otaku) and specific (the anime name, characters)]
THUMBNAIL_TEXT: [2-4 ALL CAPS punchy words — e.g., "ONE PIECE LEAK", "HUGE REVEAL"]
BANNER_TAG: [Pick ONE word: BREAKING or LEAKED or HUGE or RUMOR — this becomes the red banner]
SEARCH_TAGS: [8 hashtags starting with # for end of description]
"""

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.85,
        max_tokens=1500,
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
    banner_tag     = extract('BANNER_TAG') or 'BREAKING'
    search_tags    = extract('SEARCH_TAGS')

    if '#Shorts' not in title and '#shorts' not in title:
        title = title[:60] + ' #Shorts'

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
        'banner_tag':     banner_tag.upper().strip(),
    }
