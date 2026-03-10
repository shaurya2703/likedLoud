from pathlib import Path
from instagrapi import Client


def post_reel(video_path: str, caption: str, cl: Client) -> str:
    """
    Upload a reel to Instagram.

    Returns the URL of the new post.
    """
    print(f"[poster] Uploading {video_path}...")
    media = cl.clip_upload(
        Path(video_path),
        caption=caption,
    )
    url = f"https://www.instagram.com/reel/{media.code}/"
    print(f"[poster] Posted successfully: {url}")
    return url
