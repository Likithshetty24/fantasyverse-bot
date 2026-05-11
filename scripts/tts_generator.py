import os
import subprocess
import shutil
import numpy as np
import soundfile as sf
from moviepy.editor import AudioFileClip

KOKORO_MODEL_DIR = os.environ.get('KOKORO_MODEL_DIR', '/tmp/kokoro')
KOKORO_MODEL   = os.path.join(KOKORO_MODEL_DIR, 'kokoro-v1.0.onnx')
KOKORO_VOICES  = os.path.join(KOKORO_MODEL_DIR, 'voices.bin')


# ---------------------------------------------------------------------------
# Kokoro (human-sounding, offline ONNX)
# ---------------------------------------------------------------------------

def _kokoro_available():
    return os.path.exists(KOKORO_MODEL) and os.path.exists(KOKORO_VOICES)


def _generate_with_kokoro(text, audio_path):
    from kokoro_onnx import Kokoro

    print("[tts_generator] Loading Kokoro model...")
    kokoro = Kokoro(KOKORO_MODEL, KOKORO_VOICES)

    # Split into sentences so large texts don't OOM
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    all_samples = []
    sample_rate = None

    for i, sentence in enumerate(sentences):
        samples, sr = kokoro.create(
            sentence,
            voice="af_heart",   # warm female voice
            speed=1.05,         # slightly faster than default
            lang="en-us",
        )
        if sample_rate is None:
            sample_rate = sr
        all_samples.append(samples)

    if not all_samples:
        raise RuntimeError("Kokoro produced no audio samples")

    combined = np.concatenate(all_samples)

    # Write WAV then convert to MP3 via ffmpeg
    wav_path = audio_path.replace('.mp3', '_kokoro.wav')
    sf.write(wav_path, combined, sample_rate)

    result = subprocess.run(
        ['ffmpeg', '-y', '-i', wav_path,
         '-codec:a', 'libmp3lame', '-qscale:a', '2', audio_path],
        capture_output=True, text=True,
    )
    os.remove(wav_path)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg MP3 conversion failed: {result.stderr[-300:]}")

    print("[tts_generator] Kokoro audio saved.")
    return sample_rate


# ---------------------------------------------------------------------------
# gTTS fallback
# ---------------------------------------------------------------------------

def _generate_with_gtts(text, audio_path):
    from gtts import gTTS
    print("[tts_generator] Falling back to gTTS...")
    tts = gTTS(text=text, lang='en', slow=False, tld='com')
    tts.save(audio_path)
    print("[tts_generator] gTTS audio saved.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_voiceover(text, audio_path, subtitle_path):
    """Generate voiceover audio + SRT subtitle file."""
    if _kokoro_available():
        try:
            _generate_with_kokoro(text, audio_path)
        except Exception as e:
            print(f"[tts_generator] Kokoro failed ({e}), falling back to gTTS")
            _generate_with_gtts(text, audio_path)
    else:
        print("[tts_generator] Kokoro models not found, using gTTS")
        _generate_with_gtts(text, audio_path)

    # Build SRT from actual audio duration
    audio = AudioFileClip(audio_path)
    duration = audio.duration
    audio.close()

    _generate_srt(text, duration, subtitle_path)
    print(f"[tts_generator] Audio: {duration:.1f}s  |  SRT: {subtitle_path}")


def _generate_srt(text, duration, srt_path):
    """Proportional word-timing SRT — works for both Kokoro and gTTS."""
    words = text.split()
    if not words:
        open(srt_path, 'w').close()
        return

    time_per_word = duration / len(words)
    chunk_size = 7  # words per subtitle line

    chunks = [words[i:i + chunk_size] for i in range(0, len(words), chunk_size)]

    def fmt(seconds):
        h  = int(seconds // 3600)
        m  = int((seconds % 3600) // 60)
        s  = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    entries = []
    current = 0.0
    for i, chunk in enumerate(chunks, 1):
        chunk_dur = len(chunk) * time_per_word
        start = fmt(current)
        end   = fmt(min(current + chunk_dur, duration))
        entries.append(f"{i}\n{start} --> {end}\n{' '.join(chunk)}")
        current += chunk_dur

    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(entries) + '\n')


def vtt_to_srt(vtt_path, srt_path):
    """Copy VTT -> SRT (gTTS path writes SRT directly)."""
    if os.path.exists(vtt_path):
        shutil.copy(vtt_path, srt_path)
        print(f"[tts_generator] SRT ready: {srt_path}")
