"""
script_generator.py — The AI Stack
Generates a 45-60 second educational AI/LLM Shorts script using one of
four content formats. Each format has its own prompt tuned for the
content type — a concept explainer paces differently from a news take.
"""

import os
import re
from groq import Groq
from datetime import datetime


HUMAN_VOICE_RULES = """
WRITING STYLE — sound like a smart developer talking to other developers:
- Use contractions everywhere: don't, won't, that's, you'll, it's, gonna
- Short sentences, mix lengths. Most under 14 words.
- Drop technical-but-casual filler: "okay so", "look", "honestly", "here's the thing"
- Strategic ellipses for natural pauses on key reveals
- Tone: confident engineer who's been building with this stuff, not lecturing
- Personal hooks: "I built X with this last week", "If you've ever wondered..."
- NEVER say AI-narrator phrases: "In this video we will discuss", "Welcome back",
  "Today's topic is", "Let's dive in", "In conclusion"
- Avoid corporate marketing-speak. No "revolutionary", "game-changing",
  "next-generation" unless ironic
- Subscribe ask: casual — "drop a follow if you want more", "hit subscribe for
  daily AI", never "smash that subscribe button"
""".strip()


META_BLOCK_INSTRUCTIONS = """
After the script, output EXACTLY this block:

TITLE: Follow these RULES EXACTLY:
  - 45-65 characters total (counting "#Shorts" at the end)
  - Format: [topic / tool / concept] [hook] #Shorts
  - Topic name MUST appear in the first 30 characters
  - MUST include one curiosity/value word: WHY, HOW, EXPLAINED, BEFORE, NEVER, ACTUALLY, REAL, BROKEN, INSANE, IGNORED, OVERRATED
  - "#Shorts" goes ONLY at the end, never at the start, exactly once
  - NO emojis. NO three-caps-in-a-row spam.
  GOOD examples:
    ✓ "RAG explained in 60 seconds — what they got wrong #Shorts"
    ✓ "Why MCP is about to change every AI app #Shorts"
    ✓ "Cursor vs Windsurf — the honest comparison #Shorts"
    ✓ "Claude Code in 60 seconds — agentic coding is here #Shorts"
  BAD examples:
    ✗ "AI is great #Shorts"               (no specifics, no hook)
    ✗ "#Shorts intro to AI"               (Shorts at start, no value word)
    ✗ "AI Tutorial 🤖🔥 #Shorts"           (emojis)

DESCRIPTION: [100-140 words, casual technical tone, expand on the concept,
              include 2-3 relevant links if the topic has obvious official docs
              (Anthropic, OpenAI, LangChain, etc.) — end with casual follow CTA]
TAGS: [15 comma-separated tags — mix broad (AI, LLM, machine learning, ai engineer)
       and specific (the actual topic/tool name, related concepts)]
THUMBNAIL_TEXT: [2-4 ALL CAPS punchy words — e.g., "RAG EXPLAINED", "MCP IS NEW",
                 "CLAUDE CODE 101"]
BANNER_TAG: [Pick ONE: NEW or HOT or EXPLAINER or TOOL or NEWS or BREAKING]
SEARCH_TAGS: [8 hashtags starting with #: #AI #LLM #LangChain #ClaudeCode #Anthropic etc]
""".strip()


# ---------------------------------------------------------------------------
# Per-format prompts
# ---------------------------------------------------------------------------

def _prompt_news_commentary(news):
    return f"""You are an experienced AI engineer writing the daily Shorts script for "The AI Stack" — a channel teaching agentic AI, LLMs, and the modern AI stack to developers.

TODAY'S NEWS:
Headline: {news['title']}
Context: {news['summary']}
Source: {news['source']}

Write a 45-60 second take on this news that's informative AND has a point of view.

STRUCTURE:
1. HOOK (5-8 words, 0-3 sec) — sharp claim or surprising frame
   Examples: "Anthropic just changed how agents work.", "OpenAI's new release is more important than people think."
2. THE NEWS (5-15 sec) — what happened, in plain English. One short paragraph.
3. WHY IT MATTERS (15-40 sec) — 2-3 specific implications. What changes for developers?
   What does it mean if you're building with LLMs today?
4. CLOSING (40-55 sec) — a clear take + a question that invites engagement.
   End with a casual subscribe ask.

LENGTH: 110-150 words.

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


def _prompt_concept_explainer(topic_title, topic_summary):
    return f"""You are an AI engineer writing the daily concept-explainer Short for "The AI Stack".

TODAY'S CONCEPT:
{topic_title}
What it is: {topic_summary}

Explain this concept in 45-60 seconds in a way that makes a developer go "oh, that's actually useful."

STRUCTURE:
1. HOOK (5-8 words, 0-3 sec) — bold claim or curiosity gap
   Examples: "Most devs misunderstand RAG.", "MCP is the AI equivalent of USB-C."
2. SIMPLE DEFINITION (5-15 sec) — one-sentence explanation a junior dev would understand
3. CONCRETE EXAMPLE (15-40 sec) — show, don't tell. Walk through a tiny scenario
   or compare two approaches (with vs without). Use specific names where natural.
4. WHY YOU SHOULD CARE (40-55 sec) — when you'd reach for this in real code +
   one closing line that lands. End with casual subscribe ask.

LENGTH: 110-150 words.

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


def _prompt_tool_spotlight(topic_title, topic_summary):
    return f"""You are an AI engineer writing the daily tool-spotlight Short for "The AI Stack".

TODAY'S TOOL:
{topic_title}
What it does: {topic_summary}

Sell this tool to developers in 45-60 seconds — but honestly. Real benefits, one limitation.

STRUCTURE:
1. HOOK (5-8 words, 0-3 sec) — claim or comparison
   Examples: "Cursor isn't just VS Code with AI.", "Ollama runs Llama on your laptop in 60 seconds."
2. WHAT IT IS (5-15 sec) — one sentence positioning + the main thing it replaces
3. WHY IT'S GOOD (15-35 sec) — 2 concrete reasons devs love it
4. ONE HONEST DOWNSIDE (35-45 sec) — credibility move — one limitation
5. CLOSING (45-55 sec) — when you'd actually reach for it + casual subscribe ask

LENGTH: 110-150 words.

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


def _prompt_certification(topic_title, topic_summary):
    return f"""You are an AI engineer writing the daily certification/career Short for "The AI Stack".

TODAY'S TOPIC:
{topic_title}
Context: {topic_summary}

Give developers a 45-60 second roadmap or insight. Career angle. What to actually do this week.

STRUCTURE:
1. HOOK (5-8 words, 0-3 sec) — value-driven claim
   Examples: "The AWS AI cert opens more doors than people think.", "Most prompt engineer jobs are gone — here's what replaced them."
2. THE CONTEXT (5-15 sec) — what this is, who it's for
3. THE PATH OR TRUTH (15-40 sec) — concrete steps or honest assessment
4. WHAT TO DO THIS WEEK (40-55 sec) — one specific action viewer can take now +
   casual subscribe ask

LENGTH: 110-150 words.

{HUMAN_VOICE_RULES}

{META_BLOCK_INSTRUCTIONS}
"""


PROMPT_DISPATCH = {
    'news_commentary':   None,  # special: takes news dict
    'concept_explainer': _prompt_concept_explainer,
    'tool_spotlight':    _prompt_tool_spotlight,
    'certification':     _prompt_certification,
}


# ---------------------------------------------------------------------------
# Title polish
# ---------------------------------------------------------------------------

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF"
    "]+",
    flags=re.UNICODE,
)


def _polish_title(raw_title):
    t = raw_title.strip().strip('"\'')
    t = _EMOJI_RE.sub('', t)
    t = re.sub(r'#\s*[Ss]horts?', '', t)
    t = re.sub(r'!{2,}', '!', t)
    t = re.sub(r'\?{2,}', '?', t)
    t = re.sub(r'\s+', ' ', t).strip(' -–—:|')

    suffix = " #Shorts"
    max_body = 65 - len(suffix)
    if len(t) > max_body:
        t = t[:max_body].rstrip(' .,;:!-–—')
    return f"{t}{suffix}"


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def generate_script_and_metadata(topic):
    client = Groq(api_key=os.environ['GROQ_API_KEY'])
    content_type = topic.get('content_type', 'concept_explainer')

    if content_type == 'news_commentary':
        prompt = _prompt_news_commentary(topic['news'])
    else:
        builder = PROMPT_DISPATCH.get(content_type) or _prompt_concept_explainer
        prompt = builder(topic['topic_title'], topic['topic_summary'])

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

    title          = _polish_title(extract('TITLE'))
    description    = extract('DESCRIPTION')
    tags_raw       = extract('TAGS')
    tags           = [t.strip() for t in tags_raw.split(',') if t.strip()]
    thumbnail_text = extract('THUMBNAIL_TEXT')
    banner_tag     = (extract('BANNER_TAG') or
                      ('NEWS' if content_type == 'news_commentary' else 'EXPLAINER')).upper().strip()
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
        'content_type':   content_type,
    }
