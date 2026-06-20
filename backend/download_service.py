import os
import asyncio
import yt_dlp
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/download", tags=["download"])

DOWNLOAD_DIR = os.path.expanduser("~/Music/YouTube")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class DownloadRequest(BaseModel):
    ids: List[str] # Can be video IDs or Playlist IDs
    is_playlist: bool = False
    download_video: bool = False

@router.post("/start")
async def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_downloads, request.ids, request.is_playlist, request.download_video)
    return {"message": f"Started downloading {len(request.ids)} items"}

def process_downloads(ids: List[str], is_playlist: bool, download_video: bool):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best' if download_video else 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'download_archive': os.path.join(DOWNLOAD_DIR, 'archive.txt'), # Skips already downloaded
        'referer': 'https://www.youtube.com/',
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'extractor_args': {'youtube': {'player_client': ['web', 'mweb']}},
    }

    if not download_video:
        ydl_opts.update({
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320', # High quality as requested
            }],
        })
    else:
        # For high quality video, we might need ffmpeg to merge
        ydl_opts.update({
            'merge_output_format': 'mp4',
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for item_id in ids:
            try:
                if is_playlist:
                    url = f"https://www.youtube.com/playlist?list={item_id}"
                else:
                    url = f"https://www.youtube.com/watch?v={item_id}"
                ydl.download([url])
            except Exception as e:
                print(f"Error downloading {item_id}: {e}")

@router.get("/library")
async def list_local_library():
    files = []
    for filename in os.listdir(DOWNLOAD_DIR):
        if filename.endswith((".mp3", ".mp4", ".mkv", ".webm")):
            files.append({
                "name": filename,
                "path": os.path.join(DOWNLOAD_DIR, filename),
                "type": "video" if filename.endswith((".mp4", ".mkv", ".webm")) else "audio"
            })
    return files
