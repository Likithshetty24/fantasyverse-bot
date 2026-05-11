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

    prompt = f"""You are a script writer for a YouTube Shorts anime news channel called Fantasy Verse.

Today is {today}. Write a YouTube SHORT script based on these trending anime news items:

{news_block}

SCRIPT REQUIREMENTS:
- Total length: EXACTLY 200-230 words (reads in 60-75 seconds — this is a YouTube Short)
- Start with: "What is up everyone! Welcome to Fantasy Verse. Huge anime news today, let's go!"
- Pick the TOP 2-3 most exciting stories only — no fluff
- Each story: 2-3 punchy sentences with genuine hype and fan reaction
- End with: "Smash that like button, subscribe to Fantasy Verse, and drop your thoughts below. See you next Short!"
- NO section headers, NO stage directions, NO filler — tight punchy narration only

After the script output EXACTLY this block (each on its own line, nothing else after):
TITLE: [YouTube title max 70 chars, MUST contain #Shorts, year, power word like HUGE or SHOCKING]
DESCRIPTION: [80-120 word YouTube description, naturally include keywords, end with subscribe CTA]
TAGS: [15 comma-separated tags, mix of broad and specific anime terms]
THUMBNAIL_TEXT: [3-5 ALL CAPS bold words for thumbnail overlay]
SEARCH_TAGS: [8 hashtags starting with # for end of description]
"""

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.8,
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
    search_tags    = extract('SEARCH_TAGS')

    # Ensure #Shorts is in the title (required for YouTube Shorts discovery)
    if '#Shorts' not in title and '#shorts' not in title:
        title = title[:65] + ' #Shorts'

    full_description = f"{description}\n\n{search_tags}"

    print(f"[script_generator] Script: {len(script.split())} words")
    print(f"[script_generator] Title: {title}")

    return {
        'script':         script,
        'title':          title,
        'description':    full_description,
        'tags':           tags,
        'thumbnail_text': thumbnail_text,
    }
