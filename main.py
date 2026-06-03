import os
import subprocess
import json
import re
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import yt_dlp

# Get absolute paths for static and templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Ensure directories exist
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

class VideoURL(BaseModel):
    url: str

def sanitize_filename(filename):
    return re.sub(r'(?u)[^-\w.]', '', filename.strip().replace(' ', '_'))

def get_video_info(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.post("/info")
async def video_info(video: VideoURL):
    info = get_video_info(video.url)
    return {
        "title": info.get('title'),
        "thumbnail": info.get('thumbnail'),
        "duration": info.get('duration'),
        "uploader": info.get('uploader'),
        "id": info.get('id')
    }

@app.get("/download")
def download(url: str, type: str = "video", title: str = "download"):
    safe_title = sanitize_filename(title)

    if type == "audio":
        format_str = "bestaudio/best"
        ext = "mp3"
        media_type = "audio/mpeg"

        ydl_opts = {'format': format_str, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            user_agent = ydl_opts.get('user_agent', 'Mozilla/5.0')

        ffmpeg_cmd = [
            "ffmpeg",
            "-user_agent", user_agent,
            "-i", audio_url,
            "-f", "mp3",
            "-acodec", "libmp3lame",
            "-ab", "192k",
            "pipe:1"
        ]
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    else:
        ext = "mp4"
        media_type = "video/mp4"

        ydl_opts = {'format': 'bestvideo[height<=1080]+bestaudio/best', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = None
            audio_url = None
            user_agent = ydl_opts.get('user_agent', 'Mozilla/5.0')
            if 'requested_formats' in info:
                for f in info['requested_formats']:
                    if f.get('vcodec') != 'none' and video_url is None:
                        video_url = f['url']
                    if f.get('acodec') != 'none' and audio_url is None:
                        audio_url = f['url']
            else:
                video_url = info['url']
                audio_url = info.get('url')

        if not video_url:
             raise HTTPException(status_code=400, detail="Could not find video stream")

        ffmpeg_cmd = [
            "ffmpeg",
            "-user_agent", user_agent,
            "-i", video_url
        ]
        if audio_url and audio_url != video_url:
            ffmpeg_cmd.extend(["-user_agent", user_agent, "-i", audio_url])

        ffmpeg_cmd.extend([
            "-map", "0:v:0",
            "-map", "1:a:0" if audio_url and audio_url != video_url else "0:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-movflags", "frag_keyframe+empty_moov+default_base_moof",
            "-f", "mp4",
            "pipe:1"
        ])

        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def iterfile():
        try:
            while True:
                chunk = process.stdout.read(1024 * 256)
                if not chunk:
                    break
                yield chunk
        finally:
            process.terminate()
            process.wait()

    filename = f"{safe_title}.{ext}"

    return StreamingResponse(
        iterfile(),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
