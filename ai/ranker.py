import json
import anthropic
from config import ANTHROPIC_API_KEY

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def rank_funniest(comments: list[dict], top_k: int = 5) -> list[dict]:
    """
    Use Claude to select the top_k funniest/most entertaining comments.

    Returns an ordered list of top_k comment dicts.
    """
    numbered = "\n".join(
        f"{i}. @{c['username']} ({c['like_count']} likes): {c['text']}"
        for i, c in enumerate(comments)
    )

    prompt = f"""You are helping curate an Instagram highlight reel of the funniest comments.

Below are {len(comments)} comments from an Instagram reel, each numbered starting at 0.
Select the {top_k} most funny, entertaining, or relatable comments.
Prioritize genuine humor, wit, and comments that will make viewers laugh.
Avoid anything offensive, hateful, or inappropriate.

Return ONLY a JSON array of the selected comment indices (0-based), ordered from funniest to least funny.
Example: [3, 0, 7, 12, 5]

Comments:
{numbered}"""

    print(f"[ranker] Asking Claude to pick top {top_k} funniest comments...")

    message = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Extract JSON array from response (handle any surrounding text)
    start = raw.find("[")
    end = raw.rfind("]") + 1
    indices = json.loads(raw[start:end])

    selected = [comments[i] for i in indices[:top_k] if i < len(comments)]

    print(f"[ranker] Claude selected indices: {indices[:top_k]}")
    for i, c in enumerate(selected, 1):
        print(f"  {i}. @{c['username']}: {c['text'][:70]}")

    return selected
