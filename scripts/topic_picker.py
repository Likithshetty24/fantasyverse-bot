"""
topic_picker.py
Picks today's mindset/money topic for Daulat Mantra.

Rotates daily across 4 categories of timeless wisdom applied to modern
money/discipline/mindset. No external API — content is grounded in a
curated seed-pool so it never runs out, never repeats too soon, and
never depends on flaky third-party feeds.
"""

import random
from datetime import datetime

# Each entry = (category, seed concept, image-prompt keywords)
TOPIC_POOL = [
    # ----- Stoicism (Marcus Aurelius / Seneca / Epictetus) -----
    ('stoic', 'Memento mori — remember you will die. Spend money/time accordingly.',
     'old hourglass, dark cinematic, candle, vertical, dramatic lighting'),
    ('stoic', 'The obstacle is the way. Difficulty is the path, not the block.',
     'mountain path through fog, lone figure, sunrise, cinematic vertical'),
    ('stoic', "Amor fati — love your fate. Make peace with reality before changing it.",
     'lone sage on cliff at sunset, peaceful, golden hour, vertical'),
    ('stoic', 'Wealth is freedom from desire, not abundance of possessions.',
     'empty zen room, single oil lamp, peaceful, dark wood, vertical'),
    ('stoic', 'Control what you can — your action, your judgment. Drop the rest.',
     'calm ocean horizon, dawn light, minimal, cinematic vertical'),
    ('stoic', "What stands in the way becomes the way.",
     'climber scaling rock face, golden light, dramatic, vertical'),
    ('stoic', 'Discomfort today is freedom tomorrow.',
     'man training alone in dim gym, sweat, intense lighting, vertical'),

    # ----- Chanakya Neeti / Indian philosophical wealth wisdom -----
    ('chanakya', 'Mitra ki pareeksha aapatti mein hoti hai. Wealth reveals true friends.',
     'two silhouettes at sunset, distance between them, dramatic, vertical'),
    ('chanakya', 'Apne dushman se bhi seekhne ki himmat rakho.',
     'ancient indian warrior with sword, golden temple background, vertical'),
    ('chanakya', "Jo aaj ki tayyari karta hai, woh kal ka raja banta hai.",
     'ancient indian king on throne, candlelit chamber, vertical, cinematic'),
    ('chanakya', 'Daulat ke teen dushman — aalas, krodh, aur lobh.',
     'three dark shadows, golden light breaking through, dramatic vertical'),
    ('chanakya', 'Sabr ke saath nadi bhi pahaad katti hai.',
     'water carving through rock canyon, time lapse feel, cinematic vertical'),
    ('chanakya', 'Apne mukabh par muskaan, aur dil mein chhupi yojana.',
     'chess board with single king piece, dramatic light, vertical'),

    # ----- Bhagavad Gita applied to money / action -----
    ('gita', 'Karma karo, phal ki chinta mat karo. Focus on input, not outcome.',
     'farmer planting seeds at dawn, sunrise field, vertical cinematic'),
    ('gita', 'Asaktah satatam karyam karma samacara — work without attachment.',
     'craftsman hands working clay, focused, warm light, vertical'),
    ('gita', "Yatra yogeshvarah krishnah — where focus goes, fortune flows.",
     'archer drawing bow, intense focus, golden hour, vertical'),
    ('gita', 'Yog karmasu kaushalam. Excellence in action IS the path.',
     'samurai sword swing, motion blur, dawn light, vertical cinematic'),

    # ----- Modern wealth psychology (Naval / Buffett / Munger) -----
    ('modern', "Ameer log time bechte nahi, kharidte hain.",
     'luxury watch close-up, dark elegant background, vertical'),
    ('modern', 'Compound interest is the 8th wonder. Compound habits is the 9th.',
     'single tree growing time-lapse feel, sunrise, vertical cinematic'),
    ('modern', "Gareeb log paisa kamaate hain. Ameer log paisa banate hain.",
     'gold coins stacking, dark dramatic light, vertical cinematic'),
    ('modern', 'Specific knowledge + leverage + accountability = wealth.',
     'lone figure at laptop, city lights at night, focused, vertical'),
    ('modern', "Ameer log soch ke kharidte hain. Gareeb log dikhane ke liye.",
     'empty luxury showroom, single spotlight on item, vertical'),
    ('modern', 'Your network is your net worth — but only useful contacts count.',
     'silhouettes shaking hands at sunset, dramatic lighting, vertical'),
    ('modern', "Asli daulat woh nahi jo dikhe, woh hai jo bachi rahe.",
     'safe vault door slightly open, golden glow inside, vertical'),
    ('modern', "Risk lena seekho, lekin sirf samajh ke baad.",
     'man on edge of cliff looking down, calm posture, vertical'),
    ('modern', "Sabse buri investment? Apne aap mein nahi.",
     'open book with golden light pouring out, vertical cinematic'),
    ('modern', "Ameer log akele paise nahi banate — vyavastha banate hain.",
     'gears and machinery turning in dark workshop, golden sparks, vertical'),

    # ----- Discipline / mindset -----
    ('mindset', "Discipline ek baar choose karo, baaki saari choices aasaan ho jaati hain.",
     'soldier silhouette at dawn, disciplined posture, vertical'),
    ('mindset', 'Comfort zone ek khoobsoorat jail hai.',
     'golden cage with door open, sunset behind, dramatic vertical'),
    ('mindset', "Sabr aur sankalp — yahi do hathiyaar kaafi hain.",
     'two ancient swords crossed, dramatic light, dark background, vertical'),
    ('mindset', "Apni soch ka master bano, naukar nahi.",
     'meditation pose on mountaintop, sunrise, peaceful, vertical'),
    ('mindset', "Jo kal ko todna chahta hai, woh aaj ki adat badle.",
     'sledgehammer breaking through wall, dust, dramatic, vertical'),
    ('mindset', 'Silent action speaks louder than loud plans.',
     'quiet workshop, hands at work, single lamp, focused, vertical'),
]


def pick_topic():
    """Deterministic daily rotation through the seed pool."""
    today = datetime.now()
    day_of_year = today.timetuple().tm_yday
    idx = day_of_year % len(TOPIC_POOL)
    category, seed, image_prompt = TOPIC_POOL[idx]

    # Small daily seed for downstream randomness (e.g. image prompt variation)
    rng_seed = today.strftime('%Y%m%d')

    print(f"[topic_picker] Day {day_of_year} -> slot {idx + 1}/{len(TOPIC_POOL)}")
    print(f"[topic_picker] Category: {category}")
    print(f"[topic_picker] Seed: {seed}")

    return {
        'category':     category,
        'seed':         seed,
        'image_prompt': image_prompt,
        'rng_seed':     rng_seed,
    }
