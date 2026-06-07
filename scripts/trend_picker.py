"""
trend_picker.py — The AI Stack
Picks today's AI/LLM/agentic-AI topic from multiple sources:

  - Reddit r/LocalLLaMA + r/MachineLearning  (community-curated, fastest)
  - Hacker News top AI stories               (high-signal, dev audience)
  - Anthropic / OpenAI / DeepMind blog RSS  (official announcements)
  - Curated evergreen topic pool             (always something to teach)

Content type rotation:
  - news_commentary    when fresh announcement matches a hot model/tool
  - concept_explainer  what is X (RAG, MCP, agents, fine-tuning, etc.)
  - tool_spotlight     daily tool/framework worth knowing
  - certification      AWS/Azure/Anthropic builder paths, AI careers
"""

import re
import random
import requests
import feedparser
from html import unescape
from datetime import datetime

# ---- Source endpoints ---------------------------------------------------
REDDIT_LLAMA = "https://www.reddit.com/r/LocalLLaMA/hot.json"
REDDIT_ML    = "https://www.reddit.com/r/MachineLearning/hot.json"
HN_API       = "https://hn.algolia.com/api/v1/search"
ANTHROPIC_RSS  = "https://www.anthropic.com/news/rss.xml"
OPENAI_RSS     = "https://openai.com/blog/rss.xml"
DEEPMIND_RSS   = "https://deepmind.google/blog/rss.xml"

USER_AGENT   = "TheAIStackBot/1.0"


CONTENT_TYPES = [
    'concept_explainer',
    'tool_spotlight',
    'certification',
    'concept_explainer',   # weight concepts higher — most evergreen value
    'tool_spotlight',
    'concept_explainer',
    'certification',
]


# ---------------------------------------------------------------------------
# Curated topic pool — never runs out of content
# ---------------------------------------------------------------------------

CURATED_TOPICS = [
    # ---- Core LLM concepts ----
    ('concept_explainer', 'RAG (Retrieval Augmented Generation)',
     'how LLMs use external knowledge bases to answer accurately'),
    ('concept_explainer', 'Vector embeddings',
     'how text becomes numbers that capture meaning'),
    ('concept_explainer', 'Context windows',
     'why your LLM forgets — and how 200K-token models change everything'),
    ('concept_explainer', 'Temperature in LLMs',
     'the single setting that controls creativity vs determinism'),
    ('concept_explainer', 'Chain-of-Thought prompting',
     'why "think step by step" makes models 2x smarter'),
    ('concept_explainer', 'Few-shot vs zero-shot prompting',
     'when examples in your prompt help and when they hurt'),
    ('concept_explainer', 'Fine-tuning vs in-context learning',
     'when to train a model vs just prompt it better'),
    ('concept_explainer', 'LoRA (Low-Rank Adaptation)',
     'how to fine-tune a 70B model on a single GPU'),
    ('concept_explainer', 'Quantization',
     'how a 70B model fits on a laptop'),
    ('concept_explainer', 'Mixture of Experts (MoE)',
     'why Mistral and DeepSeek only activate part of the model'),

    # ---- Agentic AI ----
    ('concept_explainer', 'AI agents',
     'what makes an agent more than just a chatbot'),
    ('concept_explainer', 'ReAct framework',
     'the loop that powers most modern AI agents'),
    ('concept_explainer', 'Function calling / tool use',
     'how LLMs actually do things in the real world'),
    ('concept_explainer', 'MCP (Model Context Protocol)',
     'the USB-C of AI — connect any tool to any model'),
    ('concept_explainer', 'Multi-agent systems',
     'when one agent isn\'t enough — orchestrating teams'),
    ('concept_explainer', 'Agent memory',
     'how AI agents remember across sessions and turns'),
    ('concept_explainer', 'Computer use agents',
     'AI that clicks, types, and uses apps like a human'),
    ('concept_explainer', 'Agentic coding',
     'how AI is writing entire codebases autonomously'),

    # ---- Tool spotlights ----
    ('tool_spotlight', 'Claude Code',
     'Anthropic\'s terminal-native AI pair programmer'),
    ('tool_spotlight', 'Cursor IDE',
     'the AI-first IDE that replaced VS Code for many devs'),
    ('tool_spotlight', 'Windsurf',
     'Cursor\'s biggest competitor with agentic features'),
    ('tool_spotlight', 'LangChain',
     'the framework that started the agent revolution'),
    ('tool_spotlight', 'LlamaIndex',
     'best framework for RAG over your own documents'),
    ('tool_spotlight', 'AutoGen',
     'Microsoft\'s multi-agent conversation framework'),
    ('tool_spotlight', 'CrewAI',
     'role-based multi-agent orchestration in 10 lines'),
    ('tool_spotlight', 'Ollama',
     'run LLMs locally on your laptop in 60 seconds'),
    ('tool_spotlight', 'Pinecone',
     'production vector database for RAG at scale'),
    ('tool_spotlight', 'Chroma',
     'open source vector DB that fits in a Python script'),
    ('tool_spotlight', 'vLLM',
     'serving framework that\'s 10x faster than HuggingFace'),
    ('tool_spotlight', 'v0 by Vercel',
     'AI that builds React UIs from a single prompt'),
    ('tool_spotlight', 'Bolt.new',
     'full-stack app generation in your browser'),
    ('tool_spotlight', 'Replicate',
     'API marketplace for running any open source model'),

    # ---- Certification & career ----
    ('certification', 'Anthropic Builder Path',
     'the new certification track from the makers of Claude'),
    ('certification', 'AWS AI Practitioner certification',
     'the easiest AI cert that actually opens doors'),
    ('certification', 'AWS Generative AI Specialty',
     'deeper AWS cert focused on building production LLM apps'),
    ('certification', 'Azure AI Engineer Associate',
     'Microsoft\'s certification path for AI builders'),
    ('certification', 'Google Cloud AI Engineer',
     'how to specialize in Vertex AI and Gemini deployment'),
    ('certification', 'AI engineer salary in 2026',
     'real numbers from entry-level to staff in different cities'),
    ('certification', 'Prompt engineer career path',
     'is this still a real job? what\'s changed in 2026'),
    ('certification', 'Self-taught AI engineer roadmap',
     'the 6-month plan that actually lands jobs'),
    ('certification', 'DeepLearning.AI specializations on Coursera',
     'which ones are worth your time, which to skip'),
    ('certification', 'AI consultant rates',
     'what to charge as a freelance LLM/AI specialist'),

    # ---- Models ----
    ('concept_explainer', 'Claude Sonnet vs Opus',
     'when to use which Anthropic model — and why it matters'),
    ('concept_explainer', 'Reasoning models (o1, o3 style)',
     'why these models think before they speak'),
    ('concept_explainer', 'Open source vs frontier models',
     'when DeepSeek or Llama beats GPT/Claude'),
]


# ---------------------------------------------------------------------------
# News fetchers
# ---------------------------------------------------------------------------

def _clean_text(html):
    text = re.sub(r'<[^>]+>', '', html or '')
    return re.sub(r'\s+', ' ', unescape(text)).strip()


def _fetch_reddit(url, limit=15):
    try:
        r = requests.get(url, params={'limit': limit, 't': 'day'},
                         headers={'User-Agent': USER_AGENT}, timeout=15)
        r.raise_for_status()
        items = []
        for child in r.json().get('data', {}).get('children', []):
            d = child.get('data', {}) or {}
            title = (d.get('title') or '').strip()
            if not title or d.get('over_18'):
                continue
            items.append({
                'title':   title,
                'summary': (d.get('selftext') or '')[:280],
                'link':    'https://reddit.com' + d.get('permalink', ''),
                'source':  'reddit',
            })
        return items
    except Exception as e:
        print(f"[trend_picker] Reddit fetch failed ({url[-25:]}): {e}")
        return []


def _fetch_hackernews(limit=10):
    try:
        r = requests.get(HN_API, params={
            'query':      'AI OR LLM OR agent',
            'tags':       'story',
            'numericFilters': 'points>50',
            'hitsPerPage': limit,
        }, timeout=15)
        r.raise_for_status()
        items = []
        for hit in r.json().get('hits', []):
            title = (hit.get('title') or '').strip()
            if not title:
                continue
            items.append({
                'title':   title,
                'summary': (hit.get('story_text') or '')[:280] or hit.get('url', ''),
                'link':    hit.get('url') or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                'source':  'hackernews',
            })
        return items
    except Exception as e:
        print(f"[trend_picker] HN fetch failed: {e}")
        return []


def _fetch_blog_rss(url, source_name, limit=8):
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:limit]:
            title = entry.get('title', '').strip()
            if not title:
                continue
            items.append({
                'title':   title,
                'summary': _clean_text(entry.get('summary', ''))[:280],
                'link':    entry.get('link', ''),
                'source':  source_name,
            })
        return items
    except Exception as e:
        print(f"[trend_picker] {source_name} RSS failed: {e}")
        return []


def _fetch_all_news():
    """Pool all sources, dedupe loosely by title prefix."""
    pool = []
    pool += _fetch_reddit(REDDIT_LLAMA, limit=12)
    pool += _fetch_reddit(REDDIT_ML, limit=10)
    pool += _fetch_hackernews(limit=10)
    pool += _fetch_blog_rss(ANTHROPIC_RSS, 'anthropic', limit=5)
    pool += _fetch_blog_rss(OPENAI_RSS, 'openai', limit=5)
    pool += _fetch_blog_rss(DEEPMIND_RSS, 'deepmind', limit=5)

    by_source = {}
    for item in pool:
        by_source.setdefault(item['source'], 0)
        by_source[item['source']] += 1
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
# Hot-topic keywords — for matching news to a "trending" angle
# ---------------------------------------------------------------------------

HOT_KEYWORDS = [
    'claude', 'gpt-5', 'gpt-4', 'gemini', 'llama', 'mistral', 'deepseek',
    'qwen', 'anthropic', 'openai', 'agent', 'agentic', 'rag', 'mcp',
    'fine-tune', 'fine-tuning', 'cursor', 'windsurf', 'langchain',
    'llamaindex', 'ollama', 'vector db', 'embedding', 'context window',
    'reasoning', 'o1', 'o3', 'multimodal',
]


def _score_news_item(item):
    """Higher score = more relevant/exciting for our channel."""
    text = (item['title'] + ' ' + item['summary']).lower()
    score = sum(1 for kw in HOT_KEYWORDS if kw in text)
    # Boost official announcements
    if item['source'] in ('anthropic', 'openai', 'deepmind'):
        score += 3
    # Boost very recent / high-signal Reddit posts
    if item['source'] == 'reddit':
        score += 0.5
    return score


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def pick_topic():
    today = datetime.now()
    day_of_year = today.timetuple().tm_yday

    print("[trend_picker] Fetching AI news from all sources...")
    news_items = _fetch_all_news()
    print(f"[trend_picker] Unique items: {len(news_items)}")

    # Find the highest-scoring news item — if it scores well enough,
    # use it as today's topic (news_commentary). Otherwise fall back
    # to curated topic rotation.
    scored = [(item, _score_news_item(item)) for item in news_items]
    scored.sort(key=lambda x: x[1], reverse=True)

    if scored and scored[0][1] >= 2:
        best_news, best_score = scored[0]
        print(f"[trend_picker] News-driven topic (score {best_score}, source {best_news['source']})")
        print(f"[trend_picker]   {best_news['title']}")
        return {
            'content_type': 'news_commentary',
            'news':         best_news,
            'topic_title':  best_news['title'],
            'topic_summary': best_news['summary'],
            'rng_seed':     today.strftime('%Y%m%d'),
        }

    # Fallback to curated rotation
    rng = random.Random(today.strftime('%Y%m%d'))
    # Decide the day's content_type
    content_type = CONTENT_TYPES[day_of_year % len(CONTENT_TYPES)]
    # Filter pool by type
    matching = [t for t in CURATED_TOPICS if t[0] == content_type]
    if not matching:
        matching = CURATED_TOPICS
    chosen = matching[day_of_year % len(matching)]
    _, topic_title, topic_summary = chosen

    print(f"[trend_picker] Curated rotation -> {content_type}")
    print(f"[trend_picker]   Topic: {topic_title}")

    return {
        'content_type':  content_type,
        'news':          None,
        'topic_title':   topic_title,
        'topic_summary': topic_summary,
        'rng_seed':      today.strftime('%Y%m%d'),
    }
