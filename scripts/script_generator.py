"""
script_generator.py
Director-style anime news Shorts script for Fantasy Verse.
The prompt is heavily tuned to make Groq's output sound like a real
human creator, not an AI narrator — short sentences, contractions,
casual filler, no marketing buzzwords.
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
- Strategic ellipses ("...") create natural pauses — use them at tension moments
- Sound like you're texting a friend who's also an anime fan, not reading a press release
- Personal hooks like: "I just saw this and...", "Bro, you're not ready", "Wait till you hear what they did"
- NEVER say robotic phrases: "It has been announced", "We are excited to share", "In other news"
- Replace marketing-speak with casual variants:
    "smash subscribe" → "hit follow" / "tap that subscribe" / "don't sleep on the channel"
    "amazing news" → "this is wild" / "this is actually insane"
    "stay tuned" → "I'll keep you posted" / "more on this soon"
- React like a fan, not a reporter: "yo", "no way", "I'm dead", "this hits different"
- Use specific numbers/dates if available — vague AI-sounding statements feel fake
""".strip()


def generate_script_and_metadata(news_items):
    client = Groq(api_key=os.environ['GROQ_API_KEY'])

    news_block = '\n'.join(
        f"{i+1}. {item['title']}\n   {item['summary']}"
        for i, item in enumerate(news_items)
    )

    today = datetime.now().strftime('%B %d, %Y')

    prompt = f"""You are a 23-year-old anime YouTuber writing your daily Shorts script for the channel "Fantasy Verse". You're a real fan first — you actually watch this stuff.

Today is {today}. Pick the SINGLE most exciting story from this feed and write a 30-50 second narration:

{news_block}

{HUMAN_VOICE_RULES}

STRUCTURE (write as flowing narration, no labels):

[HOOK — 5-8 words, first 2-3 sec]
Punch them in the face with a hot take or shocking claim. Examples:
- "Okay this Chainsaw Man leak is insane."
- "I literally cannot believe this just happened."
- "Bro, One Piece fans are not okay right now."

[THE NEWS — 5-15 sec]
What happened, in one or two short sentences. Be specific.

[REACTION + DETAILS — 15-40 sec]
2-3 micro-beats with your actual reaction. Reference fans on Twitter, throw in your take, build the hype or dread. Mark rumors clearly with "rumored", "supposedly", "not confirmed yet".

[CLOSING — 40-50 sec]
Drop the "so what" in one line. Ask a real question that invites debate.
Close with a casual subscribe ask — never use the words "smash" or "amazing".

LENGTH: 75-115 words. That's it. Tight. No fluff. Every sentence earns its place.

After the script, output EXACTLY this block:
TITLE: [under 70 chars, MUST include #Shorts, include the anime name, no clickbait emojis]
DESCRIPTION: [80-120 words, casual tone matching the script, end with a casual follow CTA]
TAGS: [15 comma-separated tags — mix broad (anime, manga, otaku, anime news 2026) and specific anime/character names]
THUMBNAIL_TEXT: [2-4 ALL CAPS punchy words — e.g., "JJK SHOCKER", "OP IS COOKED"]
BANNER_TAG: [Pick ONE: BREAKING or LEAKED or HUGE or RUMOR — for the on-screen red banner]
SEARCH_TAGS: [8 hashtags starting with #]
"""

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.9,   # Slightly higher for more varied phrasing
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
