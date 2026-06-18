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
                                 get_match_events_text, get_match_goals, has_api_key)
from script_generator   import generate_match_news, generate_script_and_metadata
from tts_generator      import generate_voiceover
from footage_fetcher    import fetch_footage
from news_image_fetcher import search_match_images
from video_clip_fetcher import fetch_broll
from graphics           import make_scoreline_clip
from thumbnail_generator import generate_thumbnail
from video_assembler    import build_video
from youtube_uploader   import upload_video, upload_thumbnail

WORK_DIR   = '/tmp/extra_time_match'
STATE_DIR  = os.path.join(os.path.dirname(__file__), '..', 'data')
STATE_FILE = os.path.join(STATE_DIR, 'posted_events.json')

# Quality over quantity: never post more than this many reaction videos
# per UTC day. Flooding a young channel hurts reach — pick the biggest games.
MAX_PER_DAY = 3

# Big footballing nations get priority when more events are pending than
# the daily slots allow. Matched as case-insensitive substrings.
BIG_TEAMS = [
    'argentina', 'brazil', 'france', 'england', 'spain', 'germany',
    'portugal', 'netherlands', 'italy', 'belgium', 'uruguay', 'croatia',
    'united states', 'usa', 'mexico', 'japan', 'morocco', 'colombia',
]


def _load_state():
    """Return (posted_set, daily_counts_dict). Migrates the old list format."""
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):          # old format = just posted keys
            return set(data), {}
        return set(data.get('posted', [])), dict(data.get('daily', {}))
    except Exception:
        return set(), {}


def _save_state(posted, daily):
    os.makedirs(STATE_DIR, exist_ok=True)
    # Keep only the last ~10 days of counters so the file stays small
    if len(daily) > 10:
        for k in sorted(daily)[:-10]:
            daily.pop(k, None)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'posted': sorted(posted), 'daily': daily}, f, indent=2)


def _priority(item):
    """Higher = more important. Big teams first, full-time over half-time."""
    match, phase, _ = item
    names = (match['home'] + ' ' + match['away']).lower()
    score = 0
    if any(t in names for t in BIG_TEAMS):
        score += 10
    if phase == 'FULL-TIME':
        score += 2
    return score


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

        # Star-performance hijack: if someone bagged a brace/hat-trick at
        # FULL-TIME, post a spicy GOAT/debate video about THAT player instead
        # of a generic recap — these drive far more engagement.
        star_player, star_count = None, 0
        if phase == 'FULL-TIME':
            for name, c in get_match_goals(match['id']).items():
                if c >= 2 and c > star_count:
                    star_player, star_count = name, c

        if star_player:
            feat = 'hat-trick' if star_count >= 3 else 'brace'
            print(f"[monitor] Star performance: {star_player} {feat} "
                  f"({star_count} goals) -> debate video")
            topic = {
                'content_type':  'debate',
                'topic_title':   f"{star_player} just scored a {feat} — is he the GOAT now?",
                'topic_summary': (f"{star_player} scored a {feat} ({star_count} goals) in "
                                  f"{match['home']} {match['home_score']}-{match['away_score']} "
                                  f"{match['away']}. Spicy GOAT/rivalry hot take, grounded in "
                                  f"this performance."),
                'image_subject': star_player,
                'rng_seed':      f"{match['id']}{phase}",
            }
            meta = generate_script_and_metadata(topic)
        else:
            meta = generate_match_news(match, phase)

        audio_path = os.path.join(run_dir, 'vo.mp3')
        generate_voiceover(meta['script'], audio_path)

        images_dir = os.path.join(run_dir, 'images')
        image_paths = fetch_footage(
            image_subject=meta['image_subject'],   # [home, away]
            output_dir=images_dir,
            pexels_key=os.environ.get('PEXELS_API_KEY', ''),
            target_count=8,
            rng_seed=f"{match['id']}{phase}",
        )

        # Current, match-specific images (Reddit r/soccer) — shown first
        live_dir = os.path.join(run_dir, 'live')
        live_paths = search_match_images(match['home'], match['away'], live_dir, max_n=3)
        image_paths = live_paths + image_paths

        # Free B-roll clips for real motion
        broll_dir = os.path.join(run_dir, 'broll')
        video_clip_paths = fetch_broll(
            output_dir=broll_dir,
            pexels_key=os.environ.get('PEXELS_API_KEY', ''),
            pixabay_key=os.environ.get('PIXABAY_API_KEY', ''),
            target_clips=4,
        )

        # Animated scoreline reveal at the start
        phase_label = 'HALF TIME' if phase == 'HALF-TIME' else 'FULL TIME'
        try:
            scoreline = make_scoreline_clip(
                match['home'], match['away'],
                int(match['home_score']), int(match['away_score']),
                phase=phase_label,
            )
            pre_clips = [scoreline]
        except Exception as e:
            print(f"[monitor] Scoreline graphic failed (skipping): {e}")
            pre_clips = []

        thumb = os.path.join(run_dir, 'thumb.jpg')
        generate_thumbnail(image_paths, meta['thumbnail_text'], thumb)

        out = os.path.join(run_dir, 'video.mp4')
        build_video(image_paths, audio_path, out, banner_tag=meta['banner_tag'],
                    video_clip_paths=video_clip_paths, pre_clips=pre_clips)

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

    posted, daily = _load_state()
    today = datetime.utcnow().strftime('%Y-%m-%d')
    posted_today = daily.get(today, 0)
    remaining = MAX_PER_DAY - posted_today

    if remaining <= 0:
        print(f"[monitor] Daily cap reached ({posted_today}/{MAX_PER_DAY} "
              f"for {today}). Exiting.")
        return

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

    # Prioritize the biggest matches, then cap to remaining daily slots.
    queue.sort(key=_priority, reverse=True)
    selected = queue[:remaining]
    skipped  = len(queue) - len(selected)
    print(f"[monitor] {len(queue)} new event(s); posting {len(selected)} "
          f"(cap {MAX_PER_DAY}/day, {posted_today} already today)"
          + (f", skipping {skipped} lower-priority" if skipped else ""))

    os.makedirs(WORK_DIR, exist_ok=True)
    for match, phase, key in selected:
        try:
            _make_reaction_video(match, phase)
            posted.add(key)
            daily[today] = daily.get(today, 0) + 1
            _save_state(posted, daily)   # save after each so a crash doesn't re-post
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
