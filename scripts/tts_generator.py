"""
tts_generator.py
English voiceover for Fantasy Verse anime news.
Uses gTTS then speeds it up with ffmpeg atempo to hit ~180 wpm
(announcer-style energy) instead of gTTS's default ~130 wpm.
"""

import os
import subprocess
from gtts import gTTS
from moviepy.editor import AudioFileClip

VO_SPEED = 1.35  # 1.0 = gTTS default (~130 wpm) ; 1.35 ≈ 175 wpm


def generate_voiceover(text, audio_path):
    """Generate sped-up English voiceover. Returns duration in seconds."""
    print("[tts_generator] Generating English voiceover with gTTS...")

    raw_path = audio_path.replace('.mp3', '_raw.mp3')
    tts = gTTS(text=text, lang='en', tld='com', slow=False)
    tts.save(raw_path)

    # Speed up + add a touch of brightness for "announcer" feel
    cmd = [
        'ffmpeg', '-y', '-i', raw_path,
        '-af', f'atempo={VO_SPEED},highpass=f=80,lowpass=f=12000',
        '-codec:a', 'libmp3lame', '-qscale:a', '2',
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[tts_generator] ffmpeg filter failed, using raw: {result.stderr[-200:]}")
        import shutil
        shutil.copy(raw_path, audio_path)

    if os.path.exists(raw_path):
        os.remove(raw_path)

    clip = AudioFileClip(audio_path)
    duration = clip.duration
    clip.close()

    print(f"[tts_generator] Voiceover: {duration:.1f}s @ ~{int(130*VO_SPEED)} wpm")
    return duration
