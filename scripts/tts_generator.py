"""
tts_generator.py
Hindi voiceover for Daulat Mantra.
gTTS only has one Hindi voice, so we create variation through tempo
and pitch ffmpeg tweaks — gives the channel 4 distinct-feeling "hosts"
that rotate through the week.

Plus a podcast-mic EQ chain so it doesn't sound like raw TTS.
"""

import os
import random
import subprocess
from datetime import datetime
from gtts import gTTS
from moviepy.editor import AudioFileClip


# Tempo around 1.05-1.15 keeps Hindi intelligible (Hindi has more
# syllables per word than English, so we can't push as fast).
# Pitch variation gives the impression of different speakers.
VOICE_PROFILES = [
    {'name': 'गुरु शैली (calm guru)',     'tempo': 1.05, 'pitch': 0.94},
    {'name': 'भाई शैली (older brother)',  'tempo': 1.12, 'pitch': 0.98},
    {'name': 'दोस्त शैली (close friend)', 'tempo': 1.15, 'pitch': 1.02},
    {'name': 'गहन शैली (deep sage)',     'tempo': 1.02, 'pitch': 0.90},
]

SAMPLE_RATE = 24000


def _pick_voice():
    """Deterministic daily rotation."""
    day = datetime.now().timetuple().tm_yday
    base = VOICE_PROFILES[day % len(VOICE_PROFILES)]

    # Tiny daily randomness so even repeat profiles sound fresh
    rng = random.Random(datetime.now().strftime('%Y%m%d'))
    profile = dict(base)
    profile['tempo'] += rng.uniform(-0.02, 0.02)
    profile['pitch'] += rng.uniform(-0.01, 0.01)
    return profile


def generate_voiceover(text, audio_path):
    profile = _pick_voice()
    print(f"[tts_generator] Voice: {profile['name']}  "
          f"tempo={profile['tempo']:.2f}  pitch={profile['pitch']:.2f}")

    raw_path = audio_path.replace('.mp3', '_raw.mp3')
    tts = gTTS(text=text, lang='hi', tld='co.in', slow=False)
    tts.save(raw_path)

    # Pitch shift via asetrate + resample, then atempo for speed control,
    # plus podcast-style EQ + compression + loudnorm for warmth.
    new_rate = int(SAMPLE_RATE * profile['pitch'])
    filter_chain = (
        f"asetrate={new_rate},"
        f"aresample={SAMPLE_RATE},"
        f"atempo={profile['tempo']:.3f},"
        f"highpass=f=80,"
        f"lowpass=f=10500,"
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
