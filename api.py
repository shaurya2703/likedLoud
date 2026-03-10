"""
liked_loud — Web API
"""

import uuid
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

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
from video.editor import compose_reel

app = FastAPI(title="liked_loud")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/output", StaticFiles(directory="output"), name="output")

# In-memory job store: { job_id: { status, result, error } }
jobs: dict[str, dict] = {}


@app.get("/")
def index():
    return FileResponse("static/index.html")


class ProcessRequest(BaseModel):
    url: str
    post: bool = True


def build_caption(hashtags: list[str], original_username: str) -> str:
    tags = " ".join(hashtags)
    return f"Top comments 😂\n\n{tags}\n\nCredit: @{original_username}"


def run_pipeline(job_id: str, url: str, post: bool) -> None:
    try:
        jobs[job_id]["status"] = "downloading"
        scraper = get_client(IG_SCRAPER_USERNAME, IG_SCRAPER_PASSWORD)
        reel = download_reel(url, scraper)

        jobs[job_id]["status"] = "fetching_comments"
        top_comments = get_top_comments(reel["media_pk"], scraper, n=5)

        jobs[job_id]["status"] = "rendering"
        out_video = compose_reel(reel["video_path"], top_comments, reel["original_username"])

        if post:
            jobs[job_id]["status"] = "posting"
            caption = build_caption(reel["hashtags"], reel["original_username"])
            poster = get_client(IG_POSTER_USERNAME, IG_POSTER_PASSWORD)
            new_url = post_reel(out_video, caption, poster)
            jobs[job_id]["result"] = new_url
        else:
            # Return a URL to the rendered video served from /output
            filename = out_video.split("/")[-1]
            jobs[job_id]["result"] = f"/output/{filename}"

        jobs[job_id]["status"] = "done"
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/process")
def process(req: ProcessRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "result": None, "error": None, "post": req.post}
    background_tasks.add_task(run_pipeline, job_id, req.url, req.post)
    return {"job_id": job_id}


@app.get("/status/{job_id}")
def status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]
