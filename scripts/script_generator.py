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

    prompt = f"""You are a script writer for a popular YouTube anime news channel called Fantasy Verse.

Today is {today}. Write a YouTube video script based on these trending anime news items:

{news_block}

SCRIPT REQUIREMENTS:
- Total length: 600-750 words (reads in about 4-5 minutes)
- Start with: "What is up everyone! Welcome back to Fantasy Verse, your number one source for anime news. I'm your host, and today we are covering some huge stories from the anime world. Let's dive in!"
- Cover each news item with energy and fan commentary (not just repeating the headline)
- Add your personal hype, reactions, and what fans are saying online
- End with: "That's all for today's anime news roundup! If you enjoyed this video, smash that like button and subscribe to Fantasy Verse so you never miss a single anime update. Drop your thoughts in the comments below — I want to hear from you. Peace!"
- NO section headers, NO stage directions, just clean spoken narration

After the script, output EXACTLY in this format (each on its own line):
TITLE: [YouTube title, max 70 chars, include current year, power keywords like "BIGGEST", "HUGE", "SHOCKING"]
DESCRIPTION: [150-200 word YouTube description, include keywords naturally, end with call to subscribe]
TAGS: [15 comma-separated YouTube tags, mix of broad and specific]
THUMBNAIL_TEXT: [4-6 bold words for thumbnail overlay, ALL CAPS]
SEARCH_TAGS: [10 hashtags starting with # for end of description]
"""

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.8,
        max_tokens=2048,
    )

    raw = response.choices[0].message.content

    def extract(label):
        pattern = rf'^{label}:\s*(.+?)(?=\n[A-Z_]+:|$)'
        match = re.search(pattern, raw, re.MULTILINE | re.DOTALL)
        return match.group(1).strip() if match else ''

    script_match = re.split(r'\nTITLE:', raw, maxsplit=1)
    script = script_match[0].strip()

    title = extract('TITLE')
    description = extract('DESCRIPTION')
    tags_raw = extract('TAGS')
    tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
    thumbnail_text = extract('THUMBNAIL_TEXT')
    search_tags = extract('SEARCH_TAGS')

    full_description = f"{description}\n\n{search_tags}"

    print(f"[script_generator] Script: {len(script.split())} words")
    print(f"[script_generator] Title: {title}")

    return {
        'script': script,
        'title': title,
        'description': full_description,
        'tags': tags,
        'thumbnail_text': thumbnail_text,
    }
