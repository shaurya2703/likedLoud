import re
import shutil
from pathlib import Path
from instagrapi import Client
from config import OUTPUT_DIR


def _extract_shortcode(url: str) -> str:
    """Extract the shortcode from an Instagram reel URL."""
    match = re.search(r"/reel/([A-Za-z0-9_-]+)", url)
    if not match:
        raise ValueError(f"Could not extract shortcode from URL: {url}")
    return match.group(1)


def download_reel(url: str, cl: Client) -> dict:
    """
    Download reel video and extract metadata.

    Returns:
        {
            video_path: str,
            caption: str,
            hashtags: list[str],
            original_username: str,
            media_pk: str,
        }
    """
    shortcode = _extract_shortcode(url)
    media_pk = cl.media_pk_from_code(shortcode)
    media = cl.media_info(media_pk)

    print(f"[downloader] Downloading reel from @{media.user.username}...")

    # Download to a temp path, then move to output/source.mp4
    tmp_path = cl.clip_download(media_pk, folder=OUTPUT_DIR)
    dest_path = OUTPUT_DIR / "source.mp4"
    shutil.move(str(tmp_path), str(dest_path))

    caption = media.caption_text or ""
    hashtags = re.findall(r"#\w+", caption)

    print(f"[downloader] Saved to {dest_path}")
    print(f"[downloader] Caption hashtags: {hashtags}")

    return {
        "video_path": str(dest_path),
        "caption": caption,
        "hashtags": hashtags,
        "original_username": media.user.username,
        "media_pk": str(media_pk),
    }
