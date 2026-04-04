import os
from gtts import gTTS
from moviepy.editor import AudioFileClip


def generate_voiceover(text, audio_path, subtitle_path):
    """Generate audio with gTTS and estimate subtitle timings."""
    print("[tts_generator] Generating audio with gTTS...")
    tts = gTTS(text=text, lang='en', slow=False, tld='com')
    tts.save(audio_path)
    print(f"[tts_generator] Audio saved: {audio_path}")

    # Get actual audio duration for accurate subtitle timing
    audio = AudioFileClip(audio_path)
    duration = audio.duration
    audio.close()

    _generate_srt(text, duration, subtitle_path)
    print(f"[tts_generator] Subtitles saved: {subtitle_path}")


def _generate_srt(text, duration, srt_path):
    """Estimate subtitle timings proportionally across audio duration."""
    words = text.split()
    if not words:
        open(srt_path, 'w').close()
        return

    time_per_word = duration / len(words)
    chunk_size = 6

    chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]

    def fmt(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    entries = []
    current = 0.0

    for i, chunk in enumerate(chunks, 1):
        chunk_dur = len(chunk) * time_per_word
        start = fmt(current)
        end = fmt(min(current + chunk_dur, duration))
        entries.append(f"{i}\n{start} --> {end}\n{' '.join(chunk)}")
        current += chunk_dur

    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(entries) + '\n')


def vtt_to_srt(vtt_path, srt_path):
    """Copy vtt_path to srt_path — gTTS already writes SRT format directly."""
    import shutil
    if os.path.exists(vtt_path):
        shutil.copy(vtt_path, srt_path)
        print(f"[tts_generator] SRT ready: {srt_path}")
