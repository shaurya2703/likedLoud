# liked_loud

Takes an Instagram reel URL, overlays the top comments as animated chat bubbles, and reposts it to a new account.

## How it works

1. Downloads the reel via instagrapi
2. Scrapes the top comments by likes
3. Claude picks the funniest ones
4. moviepy overlays them as comment pills on the video
5. Posts the new reel to a separate IG account

## Setup

### Requirements

- Python 3.11+
- ffmpeg (`brew install ffmpeg`)

### Install

```bash
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Fill in your credentials in .env
```

Required env vars:

| Variable | Description |
|----------|-------------|
| `IG_SCRAPER_USERNAME` | Instagram account used to scrape |
| `IG_SCRAPER_PASSWORD` | Password for scraper account |
| `IG_POSTER_USERNAME` | Instagram account used to post |
| `IG_POSTER_PASSWORD` | Password for poster account |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude |

## Usage

### CLI

```bash
python main.py https://www.instagram.com/reel/ABC123/

# Skip posting (render only)
python main.py https://www.instagram.com/reel/ABC123/ --no-post
```

### API

Start the server:

```bash
uvicorn api:app --host 0.0.0.0 --port 8080
```

**Start a job:**

```bash
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/reel/ABC123/"}'
# → {"job_id": "abc-123-..."}
```

**Poll for status:**

```bash
curl http://localhost:8080/status/abc-123-...
# → {"status": "done", "result": "https://instagram.com/reel/XYZ", "error": null}
```

Possible status values: `queued` → `downloading` → `fetching_comments` → `rendering` → `posting` → `done` / `error`

**Health check:**

```bash
curl http://localhost:8080/health
# → {"status": "ok"}
```

## Docker

```bash
docker build -t liked_loud .
docker run -p 8080:8080 --env-file .env liked_loud
```

## Deploy (Railway)

1. Push to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
3. Set the env vars listed above in the Railway dashboard
4. Railway auto-detects the Dockerfile and deploys with a public HTTPS URL

## Project structure

```
liked_loud/
├── main.py               # CLI entrypoint
├── api.py                # FastAPI web API
├── config.py             # Loads .env
├── Dockerfile
├── instagram/
│   ├── client.py         # instagrapi login + session caching
│   ├── downloader.py     # download reel + extract metadata
│   ├── comments.py       # fetch top N comments by likes
│   └── poster.py         # upload finished reel
├── ai/ranker.py          # Claude picks top 5 funniest
├── video/editor.py       # moviepy + PIL comment pill overlays
├── output/               # downloaded + rendered videos (gitignored)
└── sessions/             # instagrapi session cache (gitignored)
```
