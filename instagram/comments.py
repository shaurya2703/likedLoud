from instagrapi import Client


def get_top_comments(media_pk: str, cl: Client, n: int = 20) -> list[dict]:
    """
    Fetch the top n comments by like count for a given media.

    Returns list of dicts: { username, text, like_count }
    """
    print(f"[comments] Fetching comments for media {media_pk}...")
    raw_comments = cl.media_comments(media_pk, amount=100)

    comments = [
        {
            "username": c.user.username,
            "text": c.text,
            "like_count": c.like_count,
        }
        for c in raw_comments
        if c.text  # skip empty/deleted comments
    ]

    comments.sort(key=lambda c: c["like_count"], reverse=True)
    top = comments[:n]

    print(f"[comments] Got {len(raw_comments)} comments, returning top {len(top)}")
    for i, c in enumerate(top, 1):
        print(f"  {i:2}. ({c['like_count']:,} likes) @{c['username']}: {c['text'][:60]}")

    return top
