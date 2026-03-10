import os
import re
import textwrap
from datetime import datetime

from moviepy.editor import (
    VideoFileClip,
    CompositeVideoClip,
    ImageClip,
)
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from config import OUTPUT_DIR

MAX_CHARS = 90
LEAD_IN = 2.0
COMMENT_DURATION = 4.5
SLIDE_DUR = 0.38   # slide-in duration (seconds)
FADE_OUT = 0.25


def _truncate(text: str, max_chars: int = MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "\u2026"


def _strip_emoji(text: str) -> str:
    """Remove supplementary-plane characters (emoji) that PIL system fonts can't render."""
    return re.sub(r"[\U00010000-\U0010FFFF]", "", text).strip()


def _format_likes(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _load_fonts() -> dict:
    # Prefer SF Rounded (same font Instagram uses) → Avenir Next → Helvetica → fallback
    candidates = [
        "/System/Library/Fonts/SFNSRounded.ttf",
        "/System/Library/Fonts/Avenir Next.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return {
                    "user": ImageFont.truetype(path, 24),
                    "body": ImageFont.truetype(path, 28),
                    "meta": ImageFont.truetype(path, 21),
                    "path": path,
                }
            except OSError:
                continue
    default = ImageFont.load_default()
    return {"user": default, "body": default, "meta": default, "path": None}


def _draw_gradient_avatar(arr: np.ndarray, cx: int, cy: int, r: int) -> None:
    """Paint an orange→pink gradient circle into arr (RGBA, in-place)."""
    h, w = arr.shape[:2]
    Y, X = np.mgrid[0:h, 0:w]
    mask = (X - cx) ** 2 + (Y - cy) ** 2 <= r ** 2
    t = np.clip((Y - (cy - r)) / max(2 * r - 1, 1), 0, 1)
    arr[mask, 0] = 255
    arr[mask, 1] = (107 * (1 - t) + 64 * t).astype(np.uint8)[mask]
    arr[mask, 2] = (53 * (1 - t) + 129 * t).astype(np.uint8)[mask]
    arr[mask, 3] = 255


def _make_chat_bubble(comment: dict, video_width: int, side: str) -> np.ndarray:
    """
    Instagram DM-style chat bubble.
      side="left"  → white bubble, dark text, avatar, tail bottom-left
      side="right" → purple→orange gradient, white text, tail bottom-right
    """
    fonts = _load_fonts()
    f_user = fonts["user"]   # 24 px – username header
    f_body = fonts["body"]   # 28 px – comment body
    f_meta = fonts["meta"]   # 21 px – like count

    username = comment.get("username", "")
    raw_text = _strip_emoji(_truncate(comment.get("text", "")))
    likes = comment.get("likes", comment.get("like_count", 0))

    AVATAR_D = 40
    AVATAR_R = AVATAR_D // 2
    avatar_gap = 8
    pad_x, pad_y = 16, 12
    line_gap = 5
    corner_r = 20
    TAIL_W, TAIL_H = 10, 12   # tail triangle dimensions

    is_left = side == "left"

    # Colours
    if is_left:
        bg_fill = (240, 240, 240, 248)
        text_col = (20, 20, 20, 255)
        user_col = (100, 100, 105, 255)
        meta_col = (130, 130, 135, 255)
    else:
        bg_fill = None          # gradient – drawn with numpy
        text_col = (255, 255, 255, 255)
        user_col = (255, 255, 255, 190)
        meta_col = (255, 255, 255, 170)

    max_bubble_w = int(video_width * 0.62)

    # ── Measure ──────────────────────────────────────────────
    dummy = Image.new("RGBA", (1, 1))
    d = ImageDraw.Draw(dummy)

    username_str = f"@{username}"
    likes_str = f"\u2665 {_format_likes(likes)}" if likes > 0 else ""

    u_bb = d.textbbox((0, 0), username_str, font=f_user)
    u_w, u_h = u_bb[2] - u_bb[0], u_bb[3] - u_bb[1]

    l_w = l_h = 0
    if likes_str:
        l_bb = d.textbbox((0, 0), likes_str, font=f_meta)
        l_w, l_h = l_bb[2] - l_bb[0], l_bb[3] - l_bb[1]

    # Wrap body text
    avail_w = max_bubble_w - 2 * pad_x
    sample = d.textbbox((0, 0), "W" * 10, font=f_body)
    avg_cw = max(1, (sample[2] - sample[0]) / 10)
    chars = max(12, int(avail_w / avg_cw))

    body_lines: list[str] = []
    b_heights: list[int] = []
    b_widths: list[int] = []
    if raw_text:
        for line in textwrap.fill(raw_text, width=chars).split("\n"):
            bb = d.textbbox((0, 0), line, font=f_body)
            body_lines.append(line)
            b_heights.append(max(1, bb[3] - bb[1]))
            b_widths.append(bb[2] - bb[0])

    total_body_h = sum(b_heights) + line_gap * max(len(body_lines) - 1, 0)
    max_body_w = max(b_widths) if b_widths else 0

    # ── Bubble size ───────────────────────────────────────────
    row1_needed = u_w + (10 + l_w if likes_str else 0)
    bubble_w = min(max(row1_needed, max_body_w) + 2 * pad_x, max_bubble_w)
    bubble_h = pad_y + u_h + line_gap + total_body_h + pad_y

    # Full card image size (includes avatar space for left)
    if is_left:
        card_w = AVATAR_D + avatar_gap + bubble_w
        bx = AVATAR_D + avatar_gap   # bubble x-offset within card
    else:
        card_w = bubble_w
        bx = 0

    card_h = bubble_h + TAIL_H

    img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))

    # ── Bubble background ─────────────────────────────────────
    bx0, by0 = bx, 0
    bx1, by1 = bx + bubble_w - 1, bubble_h - 1

    if is_left:
        draw = ImageDraw.Draw(img)
        # Full rounded rect
        draw.rounded_rectangle([(bx0, by0), (bx1, by1)], radius=corner_r, fill=bg_fill)
        # Square off bottom-left corner of bubble (the tail side)
        draw.rectangle([(bx0, by1 - corner_r), (bx0 + corner_r, by1)], fill=bg_fill)
        # Tail triangle pointing left-down
        tail = [
            (bx0, by1 - corner_r + 4),
            (bx0 - TAIL_W, card_h - 2),
            (bx0 + corner_r - 4, by1),
        ]
        draw.polygon(tail, fill=bg_fill)
    else:
        # Gradient: Instagram purple #833AB4 → pink #E1306C → orange #F77737
        arr = np.array(img)
        xs = np.arange(card_w, dtype=float)
        t_x = xs / max(card_w - 1, 1)

        r_ch = np.clip(131 + (247 - 131) * t_x, 0, 255).astype(np.uint8)
        g_ch = np.clip(58  + (119 -  58) * t_x, 0, 255).astype(np.uint8)
        b_ch = np.clip(180 + ( 55 - 180) * t_x, 0, 255).astype(np.uint8)

        # Build mask: rounded rect + squared bottom-right corner + tail
        mask_img = Image.new("L", (card_w, card_h), 0)
        md = ImageDraw.Draw(mask_img)
        md.rounded_rectangle([(bx0, by0), (bx1, by1)], radius=corner_r, fill=255)
        md.rectangle([(bx1 - corner_r, by1 - corner_r), (bx1, by1)], fill=255)
        tail = [
            (bx1, by1 - corner_r + 4),
            (bx1 + TAIL_W, card_h - 2),
            (bx1 - corner_r + 4, by1),
        ]
        md.polygon(tail, fill=255)
        mask_arr = np.array(mask_img) > 0

        arr[:, :, 0] = r_ch[np.newaxis, :]
        arr[:, :, 1] = g_ch[np.newaxis, :]
        arr[:, :, 2] = b_ch[np.newaxis, :]
        arr[mask_arr, 3] = 238
        arr[~mask_arr, 3] = 0
        img = Image.fromarray(arr)

    draw = ImageDraw.Draw(img)

    # ── Avatar (left bubbles only) ────────────────────────────
    if is_left:
        av_cx = AVATAR_R
        av_cy = bubble_h - AVATAR_R - 4   # sits at bottom-left
        arr2 = np.array(img)
        _draw_gradient_avatar(arr2, av_cx, av_cy, AVATAR_R)
        img = Image.fromarray(arr2)
        draw = ImageDraw.Draw(img)

        initial = username[0].upper() if username else "?"
        i_bb = draw.textbbox((0, 0), initial, font=f_user)
        i_w, i_h = i_bb[2] - i_bb[0], i_bb[3] - i_bb[1]
        draw.text(
            (av_cx - i_w // 2, av_cy - i_h // 2),
            initial, font=f_user, fill=(255, 255, 255, 255),
        )

    # ── Text content ──────────────────────────────────────────
    tx = bx + pad_x
    y = pad_y

    # Username header
    draw.text((tx, y), username_str, font=f_user, fill=user_col)

    # Like count – right-aligned
    if likes_str:
        draw.text(
            (bx + bubble_w - pad_x - l_w, y + (u_h - l_h) // 2),
            likes_str, font=f_meta, fill=meta_col,
        )

    y += u_h + line_gap

    # Body
    for idx, line in enumerate(body_lines):
        draw.text((tx, y), line, font=f_body, fill=text_col)
        y += b_heights[idx] + line_gap

    return np.array(img)


def _make_watermark(username: str, font_size: int = 20) -> np.ndarray:
    text = f"@ {username}"
    fonts = _load_fonts()
    font = fonts.get("meta") or ImageFont.load_default()
    # Re-load at the watermark size specifically
    if fonts.get("path"):
        try:
            font = ImageFont.truetype(fonts["path"], font_size)
        except OSError:
            pass

    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0] + 20, bbox[3] - bbox[1] + 10

    img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(0, 0), (tw - 1, th - 1)], radius=th // 2, fill=(0, 0, 0, 120))
    draw.text((10, 5), text, font=font, fill=(200, 200, 200, 200))
    return np.array(img)


def compose_reel(
    video_path: str, comments: list[dict], original_username: str
) -> str:
    """
    Compose: original video + alternating DM-style comment bubbles + watermark.
    """
    print(f"[editor] Loading video: {video_path}")
    clip = VideoFileClip(video_path)
    w, h = clip.size
    duration = clip.duration
    print(f"[editor] Video: {w}x{h}, {duration:.1f}s")

    layers = [clip]

    n = len(comments)

    # ── Pre-render all bubbles ────────────────────────────────
    BUBBLE_GAP = 10   # vertical gap between stacked bubbles
    bubbles: list[tuple[np.ndarray, str]] = []
    for i, comment in enumerate(comments):
        side = "left" if i % 2 == 0 else "right"
        bubbles.append((_make_chat_bubble(comment, w, side), side))

    # ── Stack positions (top→bottom, anchored to lower screen) ─
    total_h = sum(b.shape[0] for b, _ in bubbles) + BUBBLE_GAP * (n - 1)
    stack_top_y = h - int(h * 0.04) - total_h   # 4 % margin from bottom

    ys: list[int] = []
    cur_y = stack_top_y
    for arr, _ in bubbles:
        ys.append(cur_y)
        cur_y += arr.shape[0] + BUBBLE_GAP

    # ── Timing: spread appearances across first 50 % of video ─
    # Each comment slides in, then STAYS until the video ends
    if n > 1:
        appear_interval = (duration * 0.50 - LEAD_IN) / (n - 1)
    else:
        appear_interval = 0.0

    end_all = duration - 0.4   # all bubbles fade out just before video ends

    def _pos(fx, fy, sx, st):
        """Slide from off-screen (sx) to final (fx,fy). Uses global time."""
        def fn(t):
            local = max(0.0, t - st)
            if local < SLIDE_DUR:
                p = 1 - (1 - local / SLIDE_DUR) ** 2
                return (int(sx + (fx - sx) * p), fy)
            return (fx, fy)
        return fn

    for i, ((arr, side), final_y) in enumerate(zip(bubbles, ys)):
        bh, bw = arr.shape[:2]
        start_t = LEAD_IN + i * appear_interval

        if side == "left":
            final_x = 14
            off_x = -bw - 10
        else:
            final_x = w - bw - 14
            off_x = w + 10

        bubble_clip = (
            ImageClip(arr, ismask=False)
            .set_start(start_t)
            .set_end(end_all)
            .set_position(_pos(final_x, final_y, off_x, start_t))
            .crossfadein(0.15)
            .crossfadeout(0.4)
        )
        layers.append(bubble_clip)

    # Watermark – bottom-right
    wm_arr = _make_watermark(original_username)
    wm_h, wm_w = wm_arr.shape[:2]
    layers.append(
        ImageClip(wm_arr, ismask=False)
        .set_duration(duration)
        .set_position((w - wm_w - 14, h - wm_h - 14))
    )

    final = CompositeVideoClip(layers, size=(w, h))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = str(OUTPUT_DIR / f"reel_{timestamp}.mp4")

    print(f"[editor] Rendering to {out_path}...")
    final.write_videofile(
        out_path, codec="libx264", audio_codec="aac", fps=clip.fps, logger="bar",
    )
    print(f"[editor] Done: {out_path}")
    return out_path
