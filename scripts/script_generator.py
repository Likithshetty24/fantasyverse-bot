"""
script_generator.py
Generates a 60-90 sec Hindi horror story for Raat Ki Kahaniyan,
plus YouTube metadata (title, description, tags, thumbnail text).
"""

import os
import re
from groq import Groq


MODE_INSTRUCTIONS = {
    'fiction': (
        "Write a fictional horror story with a sharp twist at the end. "
        "Build tension slowly, then deliver a shocking reveal in the final 2 sentences. "
        "Keep it grounded — no over-the-top monsters, just creeping dread."
    ),
    'true_incident': (
        "Write the story as if narrating a TRUE incident the speaker personally heard from someone. "
        "Use phrases like 'meri dost ke saath hua tha' or 'yeh sachi kahani hai'. "
        "Add specific Indian details (city, locality, year) to make it feel real."
    ),
    'folklore': (
        "Write a story rooted in Indian folklore — chudail, daayan, bhoot, pishach, aatma. "
        "Reference traditional warnings (peepal tree at night, ulte pair, white saree, etc). "
        "Style: like an elder narrating an old village tale."
    ),
}


def generate_script_and_metadata(theme):
    """
    theme = {'mode': 'fiction'|'true_incident'|'folklore', 'setting': '...'}
    """
    client = Groq(api_key=os.environ['GROQ_API_KEY'])

    mode = theme['mode']
    setting = theme['setting']
    instruction = MODE_INSTRUCTIONS[mode]

    prompt = f"""You write viral Hindi horror stories for a YouTube Shorts channel called "Raat Ki Kahaniyan".

TODAY'S STORY:
- Mode: {mode}
- Setting / theme: {setting}
- {instruction}

SCRIPT REQUIREMENTS:
- 130-170 words, in **pure Hindi Devanagari script ONLY** (no English words, no Hinglish, no roman letters)
- First sentence MUST be a hook — pull the viewer in immediately
- Tone: like someone whispering a scary story to a friend at night
- Build dread gradually, then end with a chilling twist or revelation in the last 2 sentences
- DO NOT use stage directions, sound effects in brackets, or formatting — just clean narration
- End with this exact line: "अगर यह कहानी आपको डरा गई, तो चैनल को सब्सक्राइब करें और घंटी दबाएं।"

After the script, output EXACTLY this block (each on its own line):
TITLE: [Hindi Devanagari title, max 65 chars, MUST include #Shorts and a hook word like सच्ची, डरावनी, रात, भूत]
DESCRIPTION: [80-120 words in Hindi, describe story without spoiling twist, end with subscribe CTA]
TAGS: [15 comma-separated tags — mix Hindi and English, include "horror stories hindi", "scary stories", "bhoot ki kahani", etc]
THUMBNAIL_TEXT: [2-4 ALL CAPS Hindi words for thumbnail overlay, very punchy — e.g., "वो रात", "सच्ची कहानी"]
SEARCH_TAGS: [8 hashtags starting with # — mix #HorrorStories #HindiHorror #BhootKiKahani #ScaryStories etc]
"""

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

    title          = extract('TITLE')
    description    = extract('DESCRIPTION')
    tags_raw       = extract('TAGS')
    tags           = [t.strip() for t in tags_raw.split(',') if t.strip()]
    thumbnail_text = extract('THUMBNAIL_TEXT')
    search_tags    = extract('SEARCH_TAGS')

    # Ensure #Shorts in title
    if '#Shorts' not in title and '#shorts' not in title:
        title = title[:60] + ' #Shorts'

    full_description = f"{description}\n\n{search_tags}"

    print(f"[script_generator] Mode: {mode}")
    print(f"[script_generator] Script length: {len(script)} chars")
    print(f"[script_generator] Title: {title}")

    return {
        'script':         script,
        'title':          title,
        'description':    full_description,
        'tags':           tags,
        'thumbnail_text': thumbnail_text,
        'mode':           mode,
    }
