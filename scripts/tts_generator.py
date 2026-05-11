"""
tts_generator.py
English voiceover with daily voice rotation across 7 accents.
Each profile has its own tld + tempo + pitch so the channel doesn't
sound like the same speaker every day.
"""

import os
import random
import subprocess
from datetime import datetime
from gtts import gTTS
from moviepy.editor import AudioFileClip


# Each profile combines an accent (gTTS tld), a tempo multiplier (~175 wpm
# target) and a pitch shift via ffmpeg asetrate trick. The mix of all three
# gives 7 distinct-sounding "hosts" that rotate day to day.
VOICE_PROFILES = [
    {'name': 'US Hype Bro',     'tld': 'com',    'tempo': 1.34, 'pitch': 1.00},
    {'name': 'UK Calm Host',    'tld': 'co.uk',  'tempo': 1.28, 'pitch': 0.96},
    {'name': 'AU Energetic',    'tld': 'com.au', 'tempo': 1.38, 'pitch': 1.03},
    {'name': 'India Smooth',    'tld': 'co.in',  'tempo': 1.30, 'pitch': 0.98},
    {'name': 'Canada Chill',    'tld': 'ca',     'tempo': 1.32, 'pitch': 1.01},
    {'name': 'Ireland Punchy',  'tld': 'ie',     'tempo': 1.36, 'pitch': 1.02},
    {'name': 'ZA Deep',         'tld': 'co.za',  'tempo': 1.30, 'pitch': 0.94},
]

SAMPLE_RATE = 24000  # gTTS native rate


def _pick_voice():
    """Deterministic daily rotation so consecutive days vary."""
    day = datetime.now().timetuple().tm_yday
    base = VOICE_PROFILES[day % len(VOICE_PROFILES)]

    # Add tiny daily randomness so even same profile sounds fresh
    rng = random.Random(datetime.now().strftime('%Y%m%d'))
    profile = dict(base)
    profile['tempo'] += rng.uniform(-0.03, 0.03)
    profile['pitch'] += rng.uniform(-0.015, 0.015)
    return profile


def generate_voiceover(text, audio_path):
    """Render speech with the day's voice profile. Returns audio duration (s)."""
    profile = _pick_voice()
    print(f"[tts_generator] Voice: {profile['name']}  tempo={profile['tempo']:.2f}  pitch={profile['pitch']:.2f}")

    raw_path = audio_path.replace('.mp3', '_raw.mp3')
    tts = gTTS(text=text, lang='en', tld=profile['tld'], slow=False)
    tts.save(raw_path)

    # Pitch shift via asetrate trick + resample back, then atempo for speed,
    # then a mild EQ/limiter chain so the result sounds like a podcast mic.
    new_rate = int(SAMPLE_RATE * profile['pitch'])
    filter_chain = (
        f"asetrate={new_rate},"
        f"aresample={SAMPLE_RATE},"
        f"atempo={profile['tempo']:.3f},"
        f"highpass=f=85,"
        f"lowpass=f=11000,"
        f"acompressor=threshold=-18dB:ratio=3:attack=20:release=200,"
        f"loudnorm=I=-16:TP=-1.5:LRA=11"
    )

    cmd = [
        'ffmpeg', '-y', '-i', raw_path,
        '-af', filter_chain,
        '-codec:a', 'libmp3lame', '-qscale:a', '2',
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[tts_generator] Filter chain failed, using raw: {result.stderr[-300:]}")
        import shutil
        shutil.copy(raw_path, audio_path)

    if os.path.exists(raw_path):
        os.remove(raw_path)

    clip = AudioFileClip(audio_path)
    duration = clip.duration
    clip.close()

    print(f"[tts_generator] Voiceover: {duration:.1f}s")
    return duration
