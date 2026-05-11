"""
tts_generator.py
Hindi voiceover for Raat Ki Kahaniyan.
Uses gTTS with Indian Hindi voice + a subtle ffmpeg horror filter
(slight pitch down + light echo) for atmosphere.
No subtitle generation — the user wants clean, sub-free videos.
"""

import os
import subprocess
from gtts import gTTS
from moviepy.editor import AudioFileClip


def generate_voiceover(text, audio_path):
    """Generate Hindi voiceover and return its duration in seconds."""
    print("[tts_generator] Generating Hindi voiceover with gTTS...")

    raw_path = audio_path.replace('.mp3', '_raw.mp3')

    tts = gTTS(text=text, lang='hi', tld='co.in', slow=False)
    tts.save(raw_path)

    # Apply horror atmosphere: slight pitch drop + light echo
    # asetrate trick lowers pitch ~6% (47000/50000 of original).
    # aecho adds a single soft reverberation.
    cmd = [
        'ffmpeg', '-y', '-i', raw_path,
        '-af', 'asetrate=22050,aresample=22050,atempo=1.0,aecho=0.7:0.5:60:0.25',
        '-codec:a', 'libmp3lame', '-qscale:a', '2',
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # If ffmpeg filter fails, just use the raw audio
        print(f"[tts_generator] ffmpeg filter failed, using raw: {result.stderr[-300:]}")
        import shutil
        shutil.copy(raw_path, audio_path)

    if os.path.exists(raw_path):
        os.remove(raw_path)

    # Return duration
    clip = AudioFileClip(audio_path)
    duration = clip.duration
    clip.close()

    print(f"[tts_generator] Audio: {audio_path}  duration: {duration:.1f}s")
    return duration
