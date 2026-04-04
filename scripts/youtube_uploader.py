import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
CATEGORY_ENTERTAINMENT = '24'


def get_youtube_client():
    secrets = json.loads(os.environ['YOUTUBE_CLIENT_SECRETS'])
    installed = secrets['installed']

    creds = Credentials(
        token=None,
        refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],
        token_uri=installed['token_uri'],
        client_id=installed['client_id'],
        client_secret=installed['client_secret'],
        scopes=SCOPES,
    )

    return build('youtube', 'v3', credentials=creds)


def upload_video(video_path, title, description, tags):
    youtube = get_youtube_client()

    body = {
        'snippet': {
            'title': title[:100],
            'description': description,
            'tags': tags[:500],  # YouTube tag limit
            'categoryId': CATEGORY_ENTERTAINMENT,
            'defaultLanguage': 'en',
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False,
        },
    }

    media = MediaFileUpload(
        video_path,
        mimetype='video/mp4',
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10MB chunks
    )

    print(f"[youtube_uploader] Uploading: {title}")

    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"[youtube_uploader] Upload progress: {pct}%")
        except HttpError as e:
            print(f"[youtube_uploader] Upload error: {e}")
            raise

    video_id = response['id']
    print(f"[youtube_uploader] Upload complete! Video ID: {video_id}")
    print(f"[youtube_uploader] URL: https://www.youtube.com/watch?v={video_id}")
    return video_id
