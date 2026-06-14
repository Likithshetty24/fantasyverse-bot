"""
match_monitor.py — Extra Time
Runs frequently (every ~30 min via its own workflow). For each WC match that
has just reached HALF-TIME (PAUSED) or FULL-TIME (FINISHED) and hasn't been
posted yet, it generates and uploads an instant reaction Short.

State is tracked in data/posted_events.json so we never double-post the same
half-time/full-time. The workflow commits that file back to the repo.

Safe to run anytime: if there's no API key or no matches at HT/FT, it does
nothing and exits 0 (so the scheduled daily evergreen video is unaffected).
"""

import os
import sys
import json
import shutil
import traceback
from datetime import datetime

from match_schedule     import (get_recent_and_today_matches,
                                 get_match_events_text, has_api_key)
from script_generator   import generate_match_news
from tts_generator      import generate_voiceover
from footage_fetcher    import fetch_footage
from thumbnail_generator import generate_thumbnail
from video_assembler    import build_video
from youtube_uploader   import upload_video, upload_thumbnail

WORK_DIR   = '/tmp/extra_time_match'
STATE_DIR  = os.path.join(os.path.dirname(__file__), '..', 'data')
STATE_FILE = os.path.join(STATE_DIR, 'posted_events.json')


def _load_state():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_state(posted):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted(posted), f, indent=2)


def _make_reaction_video(match, phase):
    """Run the full pipeline for one HT/FT reaction. Returns video_id or None."""
    run_dir = os.path.join(WORK_DIR, f"{match['id']}_{phase}")
    os.makedirs(run_dir, exist_ok=True)
    try:
        # Enrich with goal/card events for better commentary
        match = dict(match)
        match['events_text'] = get_match_events_text(match['id'])

        print(f"\n[monitor] >>> {phase}: {match['home']} {match['home_score']}-"
              f"{match['away_score']} {match['away']}")

        meta = generate_match_news(match, phase)

        audio_path = os.path.join(run_dir, 'vo.mp3')
        generate_voiceover(meta['script'], audio_path)

        images_dir = os.path.join(run_dir, 'images')
        image_paths = fetch_footage(
            image_subject=meta['image_subject'],   # [home, away]
            output_dir=images_dir,
            pexels_key=os.environ.get('PEXELS_API_KEY', ''),
            target_count=10,
            rng_seed=f"{match['id']}{phase}",
        )

        thumb = os.path.join(run_dir, 'thumb.jpg')
        generate_thumbnail(image_paths, meta['thumbnail_text'], thumb)

        out = os.path.join(run_dir, 'video.mp4')
        build_video(image_paths, audio_path, out, banner_tag=meta['banner_tag'])

        video_id = upload_video(out, meta['title'], meta['description'], meta['tags'])
        if os.path.exists(thumb):
            upload_thumbnail(video_id, thumb)
        print(f"[monitor] Uploaded {phase} reaction: "
              f"https://youtube.com/watch?v={video_id}")
        return video_id
    finally:
        if os.path.exists(run_dir):
            shutil.rmtree(run_dir, ignore_errors=True)


def main():
    print(f"\n{'='*60}")
    print(f"Extra Time — Match Monitor  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")

    if not has_api_key():
        print("[monitor] FOOTBALL_DATA_API_KEY not set — nothing to monitor. Exiting.")
        return

    posted = _load_state()
    matches = get_recent_and_today_matches()

    # Build the queue of new HT/FT events
    queue = []
    for m in matches:
        mid, status = m['id'], m['status']
        if status == 'PAUSED':
            key = f"{mid}:HT"
            if key not in posted:
                queue.append((m, 'HALF-TIME', key))
        elif status == 'FINISHED':
            key = f"{mid}:FT"
            if key not in posted:
                queue.append((m, 'FULL-TIME', key))

    if not queue:
        print("[monitor] No new half-time/full-time events. Exiting.")
        return

    print(f"[monitor] {len(queue)} new event(s) to post")

    os.makedirs(WORK_DIR, exist_ok=True)
    for match, phase, key in queue:
        try:
            _make_reaction_video(match, phase)
            posted.add(key)
            _save_state(posted)   # save after each so a crash doesn't re-post
        except Exception:
            print(f"[monitor] FAILED {key}:")
            traceback.print_exc()
            # don't mark posted — retry next run

    if os.path.exists(WORK_DIR):
        shutil.rmtree(WORK_DIR, ignore_errors=True)
    print("[monitor] Done.")


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
