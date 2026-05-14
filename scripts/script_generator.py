"""
script_generator.py
Daulat Mantra — daily Hindi money/mindset wisdom Shorts.

Takes a seed concept and expands it into a viral 45-65 sec Hindi script
that sounds like a real Hindi YouTuber (not AI-translated English).
"""

import os
import re
from groq import Groq
from datetime import datetime


CATEGORY_FRAMING = {
    'stoic':    "rooted in Stoic philosophy (Marcus Aurelius, Seneca, Epictetus) but applied to modern money and discipline",
    'chanakya': "rooted in Chanakya Neeti and ancient Indian wisdom, applied to today's money and life decisions",
    'gita':     "rooted in Bhagavad Gita teachings on karma, action, and detachment — applied to wealth-building today",
    'modern':   "modern wealth psychology — Naval Ravikant, Warren Buffett, Charlie Munger ideas reframed for Indian context",
    'mindset':  "discipline and mindset truths that separate the few from the many",
}


def generate_script_and_metadata(topic):
    client = Groq(api_key=os.environ['GROQ_API_KEY'])

    category = topic['category']
    seed     = topic['seed']
    framing  = CATEGORY_FRAMING.get(category, 'timeless wisdom for money and life')

    prompt = f"""You write viral Hindi mindset/money Shorts for the YouTube channel "Daulat Mantra".

TODAY'S SEED IDEA:
"{seed}"

This idea is {framing}. Expand it into a 45-65 second Hindi narration.

WRITING STYLE — sound like a real Hindi creator, NOT an AI translation:
- 100% pure Hindi in Devanagari script (देवनागरी). Do NOT use roman/English letters.
- Allow these common English-origin words written in Devanagari: मनी, माइंडसेट, फोकस, गोल, रिच, गरीब, बिज़नेस, सक्सेस, लाइफ, इन्वेस्ट, टाइम, हैबिट
- Tone: like an older brother sharing real talk with a younger one, late at night
- Short, punchy sentences. Mix lengths.
- Use natural conversational fillers: "देखो", "समझो", "सुनो", "एक बात बताऊँ", "सोच के देखो"
- Strategic pauses with "..." at moments of weight
- Reference Indian context where natural — Tata, Ambani, Dhirubhai, गली का व्यापारी, चायवाला, etc.
- AVOID: AI-sounding lines like "आज हम बात करेंगे...", "यह वीडियो आपको पसंद आए तो...", "हमारे चैनल पर..."

STRUCTURE (write as flowing narration, no labels):

1. HOOK (5-8 शब्द, 0-3 sec)
   A bold claim or sharp question that hits instantly.
   Examples: "ज़्यादातर लोग पैसा कभी नहीं समझ पाते।" / "अमीर लोग ये एक काम रोज़ करते हैं।" / "सोचो... आख़िरी बार आपने अपने आप से सच कब बोला था?"

2. THE TRUTH (5-15 sec)
   State the core principle clearly in 1-2 sentences. The seed idea, simplified.

3. EXPLAIN + EXAMPLE (15-45 sec)
   Unfold the idea. Give a relatable example — maybe a contrast between two types of people, or a small story (real or hypothetical). Make it visceral.

4. CLOSING (45-60 sec)
   End with a sharp realisation + a question that demands the viewer reflect.
   Close with a casual subscribe ask — NOT "smash subscribe", but natural like:
   "अगर ये बात सच लगी, तो चैनल पर बने रहो — रोज़ एक नई बात।" or
   "इस तरह की बातें रोज़ चाहिए? Daulat Mantra को follow कर लो।"

LENGTH: 130-180 Hindi words (Hindi gTTS reads slower than English, so ~50-60 sec).

After the script, output EXACTLY this block:
TITLE: [Hindi Devanagari title, max 65 chars, hook-style, MUST include #Shorts at the end. Examples: "अमीर लोग ये एक काम रोज़ करते हैं #Shorts", "सबसे बड़ा झूठ जो गरीब लोग मानते हैं #Shorts"]
DESCRIPTION: [80-120 word Hindi description in Devanagari, expand on the idea slightly, end with casual follow CTA]
TAGS: [15 comma-separated tags, mix Hindi-in-Devanagari and English: motivation hindi, mindset, paisa, daulat, success hindi, stoic hindi, chanakya niti, naval ravikant hindi, etc]
THUMBNAIL_TEXT: [2-4 ALL CAPS Hindi words for thumbnail overlay. Examples: "अमीर बनो", "सोच बदलो", "सच्ची दौलत"]
SEARCH_TAGS: [8 hashtags starting with #: #DaulatMantra #MindsetHindi #MotivationHindi #PaisaKaisaKamaye #SuccessHindi etc]
"""

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.85,
        max_tokens=2000,
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

    # Ensure #Shorts is at the END of the title, exactly once
    title = re.sub(r'#[Ss]horts', '', title).strip()
    title = re.sub(r'\s+', ' ', title)
    if len(title) > 60:
        title = title[:60].rstrip()
    title = f"{title} #Shorts"

    full_description = f"{description}\n\n{search_tags}"

    print(f"[script_generator] Category: {category}")
    print(f"[script_generator] Script length: {len(script.split())} words, {len(script)} chars")
    print(f"[script_generator] Title: {title}")

    return {
        'script':         script,
        'title':          title,
        'description':    full_description,
        'tags':           tags,
        'thumbnail_text': thumbnail_text,
        'category':       category,
    }
