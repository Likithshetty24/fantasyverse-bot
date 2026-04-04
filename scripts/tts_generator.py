import asyncio
import re
import edge_tts

VOICE = "en-US-GuyNeural"

async def _generate(text, audio_path, subtitle_path):
    communicate = edge_tts.Communicate(text, VOICE)
    submaker = edge_tts.SubMaker()

    with open(audio_path, 'wb') as f:
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                f.write(chunk['data'])
            elif chunk['type'] == 'WordBoundary':
                submaker.create_sub(
                    (chunk['offset'], chunk['duration']),
                    chunk['text']
                )

    with open(subtitle_path, 'w', encoding='utf-8') as f:
        f.write(submaker.generate_subs(words_in_cue=6))

def generate_voiceover(text, audio_path, subtitle_path):
    asyncio.run(_generate(text, audio_path, subtitle_path))
    print(f"[tts_generator] Audio saved: {audio_path}")
    print(f"[tts_generator] Subtitles saved: {subtitle_path}")


def vtt_to_srt(vtt_path, srt_path):
    """Convert WebVTT to SRT format for ffmpeg subtitle burning."""
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove WEBVTT header and NOTE blocks
    content = re.sub(r'^WEBVTT.*?\n\n', '', content, flags=re.DOTALL)
    content = re.sub(r'NOTE[^\n]*\n.*?\n\n', '', content, flags=re.DOTALL)

    blocks = [b.strip() for b in content.strip().split('\n\n') if b.strip()]
    srt_entries = []
    counter = 1

    for block in blocks:
        lines = block.split('\n')
        time_line = None
        text_lines = []

        for line in lines:
            if '-->' in line:
                time_line = line
            elif line and not re.match(r'^\d+$', line):
                text_lines.append(line)

        if time_line and text_lines:
            # VTT uses dots, SRT uses commas for milliseconds
            srt_time = time_line.replace('.', ',')
            text = ' '.join(text_lines)
            srt_entries.append(f"{counter}\n{srt_time}\n{text}")
            counter += 1

    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(srt_entries) + '\n')

    print(f"[tts_generator] SRT saved: {srt_path}")
