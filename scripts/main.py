"""
main.py — Extra Time
Daily football / FIFA World Cup Shorts orchestrator.
"""

import os
import sys
import shutil
import traceback
from datetime import datetime

from trend_picker        import pick_topic
from script_generator    import generate_script_and_metadata
from tts_generator       import generate_voiceover
from footage_fetcher     import fetch_footage
from news_image_fetcher  import fetch_current_images
from video_clip_fetcher  import fetch_broll
from thumbnail_generator import generate_thumbnail
from video_assembler     import build_video
from youtube_uploader    import upload_video, upload_thumbnail

WORK_DIR = '/tmp/extra_time'


def cleanup():
    if os.path.exists(WORK_DIR):
        shutil.rmtree(WORK_DIR)


def main():
    print(f"\n{'='*60}")
    print(f"Extra Time Bot  —  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    os.makedirs(WORK_DIR, exist_ok=True)

    # 1. Pick today's football topic
    print("[1/6] Picking today's football topic...")
    topic = pick_topic()

    # 2. Generate script + metadata
    print("\n[2/6] Generating script with Groq...")
    meta = generate_script_and_metadata(topic)
    script        = meta['script']
    title         = meta['title']
    description   = meta['description']
    tags          = meta['tags']
    thumb_text    = meta['thumbnail_text']
    banner_tag    = meta['banner_tag']
    image_subject = meta['image_subject']

    with open(os.path.join(WORK_DIR, 'script.txt'), 'w', encoding='utf-8') as f:
        f.write(script)

    # 3. Voiceover
    print("\n[3/6] Generating voiceover...")
    audio_path = os.path.join(WORK_DIR, 'voiceover.mp3')
    try:
        generate_voiceover(script, audio_path)
    except Exception as e:
        print(f"ERROR: TTS failed: {e}")
        sys.exit(1)

    # 4. Football imagery (real player/team art + AI scenes)
    print("\n[4/6] Fetching football imagery...")
    images_dir  = os.path.join(WORK_DIR, 'images')
    pexels_key  = os.environ.get('PEXELS_API_KEY', '')
    image_paths = fetch_footage(
        image_subject=image_subject,
        output_dir=images_dir,
        pexels_key=pexels_key,
        target_count=8,
        rng_seed=topic.get('rng_seed'),
    )

    # Current, on-topic article images (news topics only) — shown first
    if topic.get('content_type') == 'news_commentary' and topic.get('news'):
        live_dir = os.path.join(WORK_DIR, 'live')
        live_paths = fetch_current_images(topic['news'], live_dir, max_n=3)
        image_paths = live_paths + image_paths

    # 4b. Free football B-roll clips (real motion)
    print("\n[4b/6] Fetching B-roll video clips...")
    broll_dir = os.path.join(WORK_DIR, 'broll')
    video_clip_paths = fetch_broll(
        output_dir=broll_dir,
        pexels_key=pexels_key,
        pixabay_key=os.environ.get('PIXABAY_API_KEY', ''),
        target_clips=4,
    )

    # 5. Thumbnail + video
    print("\n[5/6] Generating thumbnail and video...")
    thumbnail_path = os.path.join(WORK_DIR, 'thumbnail.jpg')
    generate_thumbnail(image_paths, thumb_text, thumbnail_path)

    output_path = os.path.join(WORK_DIR, 'final_video.mp4')
    build_video(image_paths, audio_path, output_path, banner_tag=banner_tag,
                video_clip_paths=video_clip_paths)

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
