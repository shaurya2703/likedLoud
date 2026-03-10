import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
SESSIONS_DIR = BASE_DIR / "sessions"
OUTPUT_DIR = BASE_DIR / "output"

SESSIONS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

IG_POSTER_USERNAME = os.environ["IG_POSTER_USERNAME"]
IG_POSTER_PASSWORD = os.environ["IG_POSTER_PASSWORD"]
IG_SCRAPER_USERNAME = os.environ["IG_SCRAPER_USERNAME"]
IG_SCRAPER_PASSWORD = os.environ["IG_SCRAPER_PASSWORD"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
