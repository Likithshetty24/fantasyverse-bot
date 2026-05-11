"""
main.py
Orchestrator for Fantasy Verse — daily anime news Shorts.
"""

import os
import sys
import shutil
import traceback
from datetime import datetime

from news_scraper       import fetch_anime_news
from script_generator   import generate_script_and_metadata
from tts_generator      import generate_voiceover
from footage_fetcher    import fetch_footage
from thumbnail_generator import generate_thumbnail
from video_assembler    import build_video
from youtube_uploader   import upload_video, upload_thumbnail

WORK_DIR = '/tmp/fantasy_verse'


def cleanup():
    if os.path.exists(WORK_DIR):
        shutil.rmtree(WORK_DIR)


def main():
    print(f"\n{'='*60}")
    print(f"Fantasy Verse Bot  —  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    os.makedirs(WORK_DIR, exist_ok=True)

    # 1. Fetch news
    print("[1/6] Fetching trending anime news...")
    news_items = fetch_anime_news(max_items=5)
    if not news_items:
        print("ERROR: No news found.")
        sys.exit(1)
    for i, item in enumerate(news_items, 1):
        print(f"  {i}. {item['title']}")

    # 2. Generate director-style script + metadata
    print("\n[2/6] Generating script with Groq...")
    meta = generate_script_and_metadata(news_items)
    script      = meta['script']
    title       = meta['title']
    description = meta['description']
    tags        = meta['tags']
    thumb_text  = meta['thumbnail_text']
    banner_tag  = meta['banner_tag']

    with open(os.path.join(WORK_DIR, 'script.txt'), 'w', encoding='utf-8') as f:
        f.write(script)

    # 3. Voiceover (sped up)
    print("\n[3/6] Generating fast voiceover...")
    audio_path = os.path.join(WORK_DIR, 'voiceover.mp3')
    try:
        generate_voiceover(script, audio_path)
    except Exception as e:
        print(f"ERROR: TTS failed: {e}")
        sys.exit(1)

    # 4. Anime images
    print("\n[4/6] Fetching anime imagery...")
    images_dir  = os.path.join(WORK_DIR, 'images')
    pexels_key  = os.environ.get('PEXELS_API_KEY', '')
    image_paths = fetch_footage(news_items, images_dir, pexels_key, target_count=12)

    # 5. Thumbnail + video
    print("\n[5/6] Generating thumbnail and video...")
    thumbnail_path = os.path.join(WORK_DIR, 'thumbnail.jpg')
    generate_thumbnail(image_paths, thumb_text, thumbnail_path)

    output_path = os.path.join(WORK_DIR, 'final_video.mp4')
    build_video(image_paths, audio_path, output_path, banner_tag=banner_tag)

    if not os.path.exists(output_path):
        print("ERROR: Video file was not created.")
        sys.exit(1)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[main] Video size: {size_mb:.1f} MB")

    # 6. Upload
    print("\n[6/6] Uploading to YouTube...")
    video_id = upload_video(output_path, title, description, tags)
    if os.path.exists(thumbnail_path):
        upload_thumbnail(video_id, thumbnail_path)

    print(f"\n{'='*60}")
    print(f"SUCCESS! Short published.")
    print(f"Title: {title}")
    print(f"URL:   https://www.youtube.com/watch?v={video_id}")
    print(f"{'='*60}\n")

    cleanup()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        cleanup()
        sys.exit(1)
