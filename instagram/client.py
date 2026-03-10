import json
from pathlib import Path
from instagrapi import Client
from config import SESSIONS_DIR


def get_client(username: str, password: str) -> Client:
    """Log in via instagrapi, reusing a cached session if available."""
    session_file = SESSIONS_DIR / f"{username}.json"
    cl = Client()

    if session_file.exists():
        try:
            cl.load_settings(session_file)
            cl.login(username, password)
            print(f"[client] Resumed session for @{username}")
            return cl
        except Exception:
            print(f"[client] Session invalid for @{username}, re-logging in...")

    cl.login(username, password)
    cl.dump_settings(session_file)
    print(f"[client] Logged in as @{username}, session saved")
    return cl
