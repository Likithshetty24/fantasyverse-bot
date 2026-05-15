"""
main.py
Orchestrator for Fantasy Verse — trend-aware daily anime Shorts.
"""

import os
import sys
import shutil
import traceback
from datetime import datetime

from trend_picker        import pick_topic
from script_generator    import generate_script_and_metadata
from tts_generator       import generate_voiceover
from footage_fetcher     import fetch_footage, jikan_anime_id
from clip_extractor      import fetch_video_clips
from thumbnail_generator import generate_thumbnail
from video_assembler     import build_video
from youtube_uploader    import upload_video, upload_thumbnail

WORK_DIR = '/tmp/fantasy_verse'


def cleanup():
    if os.path.exists(WORK_DIR):
        shutil.rmtree(WORK_DIR)


def main():
    print(f"\n{'='*60}")
    print(f"Fantasy Verse Bot  —  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    os.makedirs(WORK_DIR, exist_ok=True)

    # 1. Pick today's trending anime + content format
    print("[1/7] Picking today's trending topic...")
    topic = pick_topic()

    # 2. Generate script + metadata
    print("\n[2/7] Generating script with Groq...")
    meta = generate_script_and_metadata(topic)
    script           = meta['script']
    title            = meta['title']
    description      = meta['description']
    tags             = meta['tags']
    thumb_text       = meta['thumbnail_text']
    banner_tag       = meta['banner_tag']
    focus_anime      = meta['focus_anime']
    focus_characters = meta['focus_characters']

    with open(os.path.join(WORK_DIR, 'script.txt'), 'w', encoding='utf-8') as f:
        f.write(script)

    # 3. Voiceover (sped up, daily-rotating accent)
    print("\n[3/7] Generating voiceover...")
    audio_path = os.path.join(WORK_DIR, 'voiceover.mp3')
    try:
        generate_voiceover(script, audio_path)
    except Exception as e:
        print(f"ERROR: TTS failed: {e}")
        sys.exit(1)

    # 4a. Targeted stills (Wallhaven + Safebooru + Jikan + Pollinations)
    print("\n[4/7] Fetching anime imagery for the focus anime...")
    images_dir  = os.path.join(WORK_DIR, 'images')
    pexels_key  = os.environ.get('PEXELS_API_KEY', '')
    image_paths = fetch_footage(
        focus_anime=focus_anime,
        focus_characters=focus_characters,
        output_dir=images_dir,
        pexels_key=pexels_key,
        target_count=10,
    )

    # 4b. Real anime motion: extract clips from official trailers
    print("\n[5/7] Fetching trailer clips for the focus anime...")
    clips_dir = os.path.join(WORK_DIR, 'clips')
    anime_id = jikan_anime_id(focus_anime)
    video_clip_paths = []
    if anime_id:
        video_clip_paths = fetch_video_clips(
            anime_id=anime_id,
            output_dir=clips_dir,
            target_clips=6,
            rng_seed=datetime.now().strftime('%Y%m%d'),
        )
    else:
        print(f"[main] Could not resolve anime ID for '{focus_anime}' — stills only")

    # 6. Thumbnail + video
    print("\n[6/7] Generating thumbnail and video...")
    thumbnail_path = os.path.join(WORK_DIR, 'thumbnail.jpg')
    generate_thumbnail(image_paths, thumb_text, thumbnail_path)

    output_path = os.path.join(WORK_DIR, 'final_video.mp4')
    build_video(
        image_paths, audio_path, output_path,
        banner_tag=banner_tag,
        video_clip_paths=video_clip_paths,
    )

    if not os.path.exists(output_path):
        print("ERROR: Video file was not created.")
        sys.exit(1)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[main] Video size: {size_mb:.1f} MB")

    # 7. Upload
    print("\n[7/7] Uploading to YouTube...")
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
