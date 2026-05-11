import os
import sys
import shutil
import traceback
from datetime import datetime

from news_scraper import fetch_anime_news
from script_generator import generate_script_and_metadata
from tts_generator import generate_voiceover, vtt_to_srt
from footage_fetcher import fetch_footage
from video_assembler import build_video
from youtube_uploader import upload_video

WORK_DIR = '/tmp/dejushetty_run'


def cleanup():
    if os.path.exists(WORK_DIR):
        shutil.rmtree(WORK_DIR)


def main():
    print(f"\n{'='*60}")
    print(f"Fantasy Verse Bot — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    os.makedirs(WORK_DIR, exist_ok=True)

    # --- Step 1: Fetch news ---
    print("[1/6] Fetching trending anime news...")
    news_items = fetch_anime_news(max_items=5)
    if not news_items:
        print("ERROR: No news found. Aborting.")
        sys.exit(1)
    for i, item in enumerate(news_items, 1):
        print(f"  {i}. {item['title']}")

    # --- Step 2: Generate script + metadata ---
    print("\n[2/6] Generating script and metadata with Gemini...")
    metadata = generate_script_and_metadata(news_items)
    script   = metadata['script']
    title    = metadata['title']
    description = metadata['description']
    tags     = metadata['tags']

    # Save script for debugging
    with open(os.path.join(WORK_DIR, 'script.txt'), 'w') as f:
        f.write(script)

    # --- Step 3: Generate voiceover ---
    print("\n[3/6] Generating voiceover with Edge TTS...")
    audio_path = os.path.join(WORK_DIR, 'voiceover.mp3')
    vtt_path   = os.path.join(WORK_DIR, 'subtitles.vtt')
    srt_path   = os.path.join(WORK_DIR, 'subtitles.srt')

    try:
        generate_voiceover(script, audio_path, vtt_path)
        vtt_to_srt(vtt_path, srt_path)
    except Exception as e:
        print(f"ERROR: TTS generation failed after retries: {e}")
        print("SOLUTION: This is a known issue with Bing blocking automated TTS requests.")
        print("Try again in a few minutes, or consider using a different TTS service.")
        sys.exit(1)

    # --- Step 4: Fetch footage ---
    print("\n[4/6] Fetching images from Pexels...")
    images_dir = os.path.join(WORK_DIR, 'images')
    api_key = os.environ.get('PEXELS_API_KEY', '')
    image_paths = fetch_footage(news_items, images_dir, api_key)

    # --- Step 5: Assemble video ---
    print("\n[5/6] Assembling video...")
    output_path = os.path.join(WORK_DIR, 'final_video.mp4')
    build_video(image_paths, audio_path, srt_path, output_path)

    if not os.path.exists(output_path):
        print("ERROR: Video file was not created. Aborting.")
        sys.exit(1)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[main] Video size: {size_mb:.1f} MB")

    # --- Step 6: Upload to YouTube ---
    print("\n[6/6] Uploading to YouTube...")
    video_id = upload_video(output_path, title, description, tags)

    print(f"\n{'='*60}")
    print(f"SUCCESS! Video published.")
    print(f"Title: {title}")
    print(f"URL: https://www.youtube.com/watch?v={video_id}")
    print(f"{'='*60}\n")

    cleanup()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        cleanup()
        sys.exit(1)
