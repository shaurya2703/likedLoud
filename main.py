#!/usr/bin/env python3
"""
liked_loud — Instagram Reel Comment Highlights

Usage: python main.py <reel_url> [--no-post]
"""

import argparse

from config import (
    IG_SCRAPER_USERNAME,
    IG_SCRAPER_PASSWORD,
    IG_POSTER_USERNAME,
    IG_POSTER_PASSWORD,
)
from instagram.client import get_client
from instagram.downloader import download_reel
from instagram.comments import get_top_comments
from instagram.poster import post_reel
from ai.ranker import rank_funniest
from video.editor import compose_reel


def build_caption(hashtags: list[str], original_username: str) -> str:
    tags = " ".join(hashtags)
    return f"Top comments 😂\n\n{tags}\n\nCredit: @{original_username}"


def main():
    parser = argparse.ArgumentParser(description="liked_loud — Reel Comment Highlights")
    parser.add_argument("url", help="Instagram reel URL")
    parser.add_argument(
        "--no-post",
        action="store_true",
        help="Skip posting; only download, rank, and render the video",
    )
    args = parser.parse_args()

    url = args.url
    print(f"\n{'='*60}")
    print(f"liked_loud — processing: {url}")
    print(f"{'='*60}\n")

    # 1. Download reel
    scraper = get_client(IG_SCRAPER_USERNAME, IG_SCRAPER_PASSWORD)
    reel = download_reel(url, scraper)
    print()

    # 2. Fetch top 20 comments
    top20 = get_top_comments(reel["media_pk"], scraper, n=5)
    print()

    # 3. Claude picks top 5 funniest
    # top5 = rank_funniest(top20, top_k=5)
    # print()

    # 4. Compose video
    out_video = compose_reel(reel["video_path"], top20, reel["original_username"])
    print()

    if args.no_post:
        print(f"\n{'='*60}")
        print(f"Video saved to: {out_video}")
        print(f"{'='*60}\n")
        return

    # 5. Build caption
    caption = build_caption(reel["hashtags"], reel["original_username"])
    print(f"[main] Caption:\n{caption}\n")

    # 6. Post reel
    poster = get_client(IG_POSTER_USERNAME, IG_POSTER_PASSWORD)
    new_url = post_reel(out_video, caption, poster)

    print(f"\n{'='*60}")
    print(f"Success! New reel posted: {new_url}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
