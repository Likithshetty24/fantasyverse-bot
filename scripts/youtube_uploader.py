import os
import json
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
CATEGORY_ENTERTAINMENT = '24'


def refresh_access_token(client_id, client_secret, refresh_token):
    """Directly call Google's token endpoint, bypassing google-auth reauth module."""
    response = requests.post(
        'https://oauth2.googleapis.com/token',
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        },
        timeout=30,
    )
    data = response.json()
    if 'error' in data:
        raise Exception(
            f"Token refresh failed: {data['error']} — {data.get('error_description', '')}\n"
            f"Full response: {data}"
        )
    return data['access_token']


def get_youtube_client():
    secrets = json.loads(os.environ['YOUTUBE_CLIENT_SECRETS'])
    creds_data = secrets.get('installed') or secrets.get('web')

    client_id = creds_data['client_id']
    client_secret = creds_data['client_secret']
    refresh_token = os.environ['YOUTUBE_REFRESH_TOKEN']

    print("[youtube_uploader] Refreshing access token...")
    access_token = refresh_access_token(client_id, client_secret, refresh_token)
    print("[youtube_uploader] Access token obtained.")

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    return build('youtube', 'v3', credentials=creds)


def upload_video(video_path, title, description, tags):
    youtube = get_youtube_client()

    body = {
        'snippet': {
            'title': title[:100],
            'description': description,
            'tags': tags,
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
        chunksize=10 * 1024 * 1024,
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
